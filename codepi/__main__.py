from __future__ import annotations
import argparse
import asyncio
from pathlib import Path
from codepi.config import load_config
from codepi.ai.openai_compat import OpenAICompatProvider
from codepi.core.session_manager import SessionManager
from codepi.tools.builtins import make_builtin_registry
from codepi.extensions.loader import ExtensionLoader
from codepi.extensions.skill_loader import SkillLoader
from codepi.core.events import BeforeAgentStartEvent
from codepi.extensions.base import Extension
from codepi.core.security import SecurityMonitor


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="codepi", description="Minimalist terminal coding assistant")
    p.add_argument("--print", dest="print_prompt", metavar="PROMPT", help="Run in print mode with given prompt")
    p.add_argument("--rpc", action="store_true", help="Run in RPC mode (JSONL stdin/stdout)")
    p.add_argument("--session", metavar="ID", help="Resume an existing session")
    p.add_argument("--model", metavar="MODEL", help="Override LLM model")
    p.add_argument("--skills-dir", metavar="DIR", action="append", dest="skills_dirs", help="Additional skills directory")
    p.add_argument("--base-url", metavar="URL", help="Override OpenAI-compatible base URL")
    p.add_argument("--config", metavar="PATH", help="Path to config.toml")
    p.add_argument("--plan", action="store_true", help="Start in plan mode (structured planning workflow)")
    p.add_argument("--auto", action="store_true", help="Start in auto mode (continuous autonomous execution)")
    sub = p.add_subparsers(dest="cmd", metavar="COMMAND", help="Available commands")
    from codepi.templates.cli import add_template_parser
    add_template_parser(sub)
    return p


async def _run(args: argparse.Namespace) -> None:
    config = load_config(Path(args.config) if args.config else None)
    # Automatic attribution hook
    try:
        from codepi.addons import attribution
        attribution.on_startup()
    except Exception as e:
        # If attribution fails we simply warn but continue
        print(f"Warning: Attribution init failed: {e}")

    # CLI overrides
    if args.model:
        config.provider.model = args.model
    if args.base_url:
        config.provider.base_url = args.base_url

    provider = OpenAICompatProvider(
        base_url=config.provider.base_url,
        api_key=config.provider.api_key,
        default_model=config.provider.model,
    )

    # Session
    sm = SessionManager(sessions_dir=config.paths.sessions_dir)
    if args.session:
        sm.load_session(args.session)
        leaves = sm.get_leaf_ids()
        if len(leaves) > 1:
            all_entries = {e.id: e for e in sm.load_all_entries()}
            print(f"\nSession has {len(leaves)} branches. Select one to resume:\n")
            for i, leaf_id in enumerate(leaves):
                if leaf_id is None:
                    continue
                entry = all_entries.get(leaf_id)
                depth = 0
                cur: str = leaf_id
                while all_entries.get(cur) and all_entries[cur].parent_id:
                    parent_id = all_entries[cur].parent_id
                    if parent_id is None:
                        break
                    cur = parent_id
                    depth += 1
                preview = ""
                if entry and entry.type == "message":
                    preview = str(entry.data.get("content", ""))[:60]
                print(f"  [{i + 1}] depth={depth}  {preview}")
            print()
            while True:
                choice = input(f"Enter branch number (1-{len(leaves)}): ").strip()
                if choice.isdigit() and 1 <= int(choice) <= len(leaves):
                    sm.set_active_leaf(leaves[int(choice) - 1])
                    break
                print("Invalid choice, try again.")
        elif len(leaves) == 1:
            sm.set_active_leaf(leaves[0])
    else:
        sm.new_session(model=config.provider.model)

    # Skills — set package skills path before loading so package skills take priority
    from codepi.extensions.skill_loader import SkillLoader as SL
    package_skills = Path(__file__).parent / "extensions" / "openspec" / "skills"
    if package_skills.exists():
        SL.set_package_skills_dir(package_skills)

    skills_dirs = [config.paths.skills_dir]
    if args.skills_dirs:
        skills_dirs += [Path(d) for d in args.skills_dirs]
    skill_loader = SkillLoader(skills_dirs=skills_dirs)

    # Tools — include skill tool with lazy loader reference
    registry = make_builtin_registry(skill_loader_getter=lambda: skill_loader)

    # Extensions
    ext_loader = ExtensionLoader(extensions_dir=config.paths.extensions_dir)
    extensions = ext_loader.load()

    # Skills — inject via a synthetic extension (metadata only, full content on-demand)
    class SkillExtension(Extension):
        name = "skill-loader"
        async def on_before_agent_start(self, event: BeforeAgentStartEvent):
            return skill_loader.inject_skills(event)

    all_extensions = [SkillExtension()] + extensions

    model = config.provider.model
    session_id = getattr(sm, '_session_id', None) or "unknown"

    # Initialize security monitor
    security_monitor = SecurityMonitor(config=config.security) if config.security.enabled else None

    # Initialize mode managers based on flags and config
    from codepi.core.modes.plan_mode import PlanModeManager, PlanModeConfig
    from codepi.core.modes.auto_mode import AutoModeManager, AutoModeConfig

    plan_mode_manager = None
    auto_mode_manager = None

    # Auto mode takes precedence if both are specified
    if args.auto or config.modes.auto.enabled:
        auto_config = AutoModeConfig(
            enabled=True,
            max_iterations=config.modes.auto.max_iterations,
            require_approval_for=config.modes.auto.require_approval_for,
            pause_on_errors=config.modes.auto.pause_on_errors,
        )
        auto_mode_manager = AutoModeManager(config=auto_config)
    elif args.plan or config.modes.plan.enabled:
        plan_config = PlanModeConfig(
            enabled=True,
            auto_advance=config.modes.plan.auto_advance,
            require_explicit_approval=config.modes.plan.require_explicit_approval,
            max_iterations=config.modes.plan.max_iterations,
        )
        plan_mode_manager = PlanModeManager(config=plan_config)

    if args.print_prompt:
        from codepi.modes.print_mode import PrintMode
        mode = PrintMode(provider=provider, session_manager=sm, model=model,
                         tool_registry=registry, extensions=all_extensions,
                         skill_loader=skill_loader)
        await mode.run(args.print_prompt)

    elif args.rpc:
        from codepi.modes.rpc import RPCMode
        mode = RPCMode(provider=provider, session_manager=sm, model=model,
                       tool_registry=registry, extensions=all_extensions,
                       skill_loader=skill_loader)
        await mode.run()

    else:
        from codepi.modes.interactive import InteractiveMode
        mode = InteractiveMode(
            provider=provider, session_manager=sm, model=model,
            session_id=session_id,
            tool_registry=registry, extensions=all_extensions,
            skill_loader=skill_loader,
            security_monitor=security_monitor,
            plan_mode_manager=plan_mode_manager,
            auto_mode_manager=auto_mode_manager,
        )
        await mode.run()


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        if args.cmd == "template":
            from codepi.templates.cli import run_template_cmd
            exit(run_template_cmd(args))
        asyncio.run(_run(args))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
