from __future__ import annotations
import argparse
import sys
from pathlib import Path
from mypi.config import load_config
from mypi.templates.registry import TemplateRegistry


def add_template_parser(sub: argparse._SubParsersAction) -> None:
    template_parser = sub.add_parser("template", help="Manage skill templates and generate slash commands")
    sub2 = template_parser.add_subparsers(dest="template_cmd", required=True)

    list_parser = sub2.add_parser("list", help="List available workflow templates")
    list_parser.add_argument("--skills-dir", type=Path, action="append",
                            help="Skills directory (can be repeated)")

    gen_parser = sub2.add_parser("generate", help="Generate command files for a target AI tool")
    gen_parser.add_argument("--tool", required=True,
                           choices=["claude", "cursor", "windsurf"],
                           help="Target AI tool")
    gen_parser.add_argument("--skills-dir", type=Path, action="append",
                            help="Skills directory (can be repeated)")
    gen_parser.add_argument("--output", type=Path, default=Path.cwd(),
                            help="Output directory (default: current directory)")

    validate_parser = sub2.add_parser("validate", help="Validate template parity")
    validate_parser.add_argument("--skills-dir", type=Path, action="append",
                               help="Skills directory (can be repeated)")


def run_template_cmd(args: argparse.Namespace) -> int:
    config = load_config(Path(args.config) if getattr(args, "config", None) else None)
    skills_dirs = [config.paths.skills_dir]
    if args.skills_dir:
        skills_dirs = [Path(d) for d in args.skills_dir]
    registry = TemplateRegistry(skills_dirs)
    registry.load_workflows()

    cmd = args.template_cmd

    if cmd == "list":
        workflows = registry._workflows
        if not workflows:
            print("No workflow templates found.")
            return 0
        print(f"Found {len(workflows)} workflow template(s):\n")
        for name, wf in sorted(workflows.items()):
            print(f"  {name}")
            print(f"    Skill:      {wf.skill.name}")
            print(f"    Description: {wf.skill.description}")
            print(f"    Category:   {wf.command_category or '(none)'}")
            print(f"    Command ID: {wf.command_id}")
            print()
        return 0

    elif cmd == "generate":
        try:
            generated = registry.generate_commands(args.tool, args.output)
            print(f"Generated {len(generated)} command file(s):")
            for f in generated:
                print(f"  {f}")
            return 0
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    elif cmd == "validate":
        errors = registry.validate_parity()
        if not errors:
            print("All templates are valid.")
            return 0
        print(f"Found {len(errors)} validation error(s):")
        for err in errors:
            print(f"  - {err}")
        return 1

    return 0
