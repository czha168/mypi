from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from mypi.extensions.skill_loader import Skill
from mypi.templates.adapters import ToolAdapter, CommandContent, ADAPTERS


@dataclass
class WorkflowTemplate:
    skill: Skill
    command_id: str | None = None
    command_tags: list[str] = field(default_factory=list)
    command_category: str | None = None


class TemplateRegistry:
    def __init__(self, skills_dirs: list[Path]):
        self.skills_dirs = [Path(d) for d in skills_dirs]
        self._workflows: dict[str, WorkflowTemplate] = {}

    def load_workflows(self) -> dict[str, WorkflowTemplate]:
        from mypi.extensions.skill_loader import SkillLoader
        loader = SkillLoader(self.skills_dirs)
        skills = loader.load_skills()
        self._workflows.clear()
        for skill in skills:
            wf_name = skill.metadata.get("workflow")
            if wf_name:
                self._workflows[wf_name] = WorkflowTemplate(
                    skill=skill,
                    command_id=skill.metadata.get("command_id", skill.name),
                    command_tags=skill.metadata.get("tags", []),
                    command_category=skill.metadata.get("category"),
                )
        return self._workflows

    def generate_commands(
        self,
        tool_id: str,
        output_dir: Path | None = None,
    ) -> list[Path]:
        adapter = ADAPTERS.get(tool_id)
        if not adapter:
            raise ValueError(f"Unknown tool adapter: {tool_id}. Available: {list(ADAPTERS.keys())}")
        output_dir = output_dir or Path.cwd()
        generated: list[Path] = []
        for wf in self._workflows.values():
            content = CommandContent(
                id=wf.command_id or wf.skill.name,
                name=wf.skill.metadata.get("name", wf.skill.name),
                description=wf.skill.description,
                category=wf.command_category or "Workflow",
                tags=list(wf.command_tags),
                body=wf.skill.body or "",
            )
            rel_path = adapter.get_file_path(content.id)
            file_path = output_dir / rel_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(adapter.format_file(content))
            generated.append(file_path)
        return generated

    def validate_parity(self) -> list[str]:
        errors: list[str] = []
        for name, wf in self._workflows.items():
            if not wf.skill.body:
                errors.append(f"Workflow '{name}' has empty skill body")
            if wf.command_id and not wf.command_category:
                errors.append(f"Workflow '{name}' has command_id but no category")
            # Check skill body references the command name
            skill_body = (wf.skill.body or "").strip()
            if skill_body:
                command_name = wf.skill.metadata.get("name", wf.skill.name)
                if command_name not in skill_body and wf.skill.name not in skill_body:
                    errors.append(f"Workflow '{name}' body may not reference skill name correctly")
        return errors
