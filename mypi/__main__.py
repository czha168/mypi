from __future__ import annotations
import argparse
import asyncio
from pathlib import Path
from mypi.config import load_config
from mypi.ai.openai_compat import OpenAICompatProvider
from mypi.core.session_manager import SessionManager
from mypi.tools.builtins import make_builtin_registry
from mypi.extensions.loader import ExtensionLoader
from mypi.extensions.skill_loader import SkillLoader
from mypi.core.events import BeforeAgentStartEvent
from mypi.extensions.base import Extension


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="mypi", description="Minimalist terminal coding assistant")
    p.add_argument("--print", dest="print_prompt", metavar="PROMPT", help="Run in print mode with given prompt")
    p.add_argument("--rpc", action="store_true", help="Run in RPC mode (JSONL stdin/stdout)")
    p.add_argument("--session", metavar="ID", help="Resume an existing session")
    p.add_argument("--model", metavar="MODEL", help="Override LLM model")
    p.add_argument("--skills-dir", metavar="DIR", action="append", dest="skills_dirs", help="Additional skills directory")
    p.add_argument("--base-url", metavar="URL", help="Override OpenAI-compatible base URL")
    p.add_argument("--config", metavar="PATH", help="Path to config.toml")
    return p


async def _run(args: argparse.Namespace) -> None:
    config = load_config(Path(args.config) if args.config else None)

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
                entry = all_entries.get(leaf_id)
                depth = 0
                cur = leaf_id
                while all_entries.get(cur) and all_entries[cur].parent_id:
                    cur = all_entries[cur].parent_id
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

    # Skills — create loader first so we can pass getter to tools
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

    if args.print_prompt:
        from mypi.modes.print_mode import PrintMode
        mode = PrintMode(provider=provider, session_manager=sm, model=model,
                         tool_registry=registry, extensions=all_extensions)
        await mode.run(args.print_prompt)

    elif args.rpc:
        from mypi.modes.rpc import RPCMode
        mode = RPCMode(provider=provider, session_manager=sm, model=model,
                       tool_registry=registry, extensions=all_extensions)
        await mode.run()

    else:
        from mypi.modes.interactive import InteractiveMode
        mode = InteractiveMode(
            provider=provider, session_manager=sm, model=model,
            session_id=session_id,
            tool_registry=registry, extensions=all_extensions,
        )
        await mode.run()


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        asyncio.run(_run(args))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
