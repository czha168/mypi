from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import yaml
from mypi.core.events import BeforeAgentStartEvent


@dataclass
class Skill:
    """Represents a skill with metadata and optional content."""
    name: str
    description: str
    file_path: Path
    compatibility: str | None = None
    body: str | None = None
    metadata: dict = field(default_factory=dict)  # Raw YAML frontmatter


def _parse_skill(path: Path, include_body: bool = False) -> Skill | None:
    """Parse a Claude Code–format skill .md file. Returns Skill object."""
    text = path.read_text()
    if not text.startswith("---"):
        return None
    try:
        # Find the closing delimiter on its own line
        close_idx = text.find("\n---", 3)
        if close_idx == -1:
            return None
        frontmatter_text = text[3:close_idx]
        frontmatter = yaml.safe_load(frontmatter_text)
        if not isinstance(frontmatter, dict) or "name" not in frontmatter:
            return None
        body = text[close_idx + 4:].strip() if include_body else None
        return Skill(
            name=frontmatter["name"],
            description=frontmatter.get("description", ""),
            file_path=path,
            compatibility=frontmatter.get("compatibility"),
            body=body,
            metadata=frontmatter,
        )
    except Exception:
        return None


class SkillLoader:
    # Package-managed skills are prepended so they take priority over user skills
    # when both define a skill with the same name.
    _package_skills_dir: Path | None = None

    @classmethod
    def set_package_skills_dir(cls, path: Path | None) -> None:
        """Set the package-managed skills directory. Call once at startup."""
        cls._package_skills_dir = path

    def __init__(self, skills_dirs: list[Path]):
        # Prepend package-managed skills so they take priority
        package = [self._package_skills_dir] if self._package_skills_dir else []
        self.skills_dirs = [p for p in package if p] + [Path(d) for d in skills_dirs]

    def load_skills_metadata(self) -> list[Skill]:
        """Load skill metadata only (name, description). Used for system prompt."""
        skills = []
        for d in self.skills_dirs:
            if not d.exists():
                continue
            for md_file in sorted(d.glob("*.md")):
                skill = _parse_skill(md_file, include_body=False)
                if skill:
                    skills.append(skill)
        return skills

    def load_skills(self) -> list[Skill]:
        """Load full skill data including body content."""
        skills = []
        for d in self.skills_dirs:
            if not d.exists():
                continue
            for md_file in sorted(d.glob("*.md")):
                skill = _parse_skill(md_file, include_body=True)
                if skill:
                    skills.append(skill)
        return skills

    def load_skill_content(self, name: str) -> Skill | None:
        """Load full content for a specific skill by name. Used for on-demand loading."""
        for d in self.skills_dirs:
            if not d.exists():
                continue
            for md_file in sorted(d.glob("*.md")):
                skill = _parse_skill(md_file, include_body=True)
                if skill and skill.name == name:
                    return skill
        return None

    def inject_skills(self, event: BeforeAgentStartEvent) -> BeforeAgentStartEvent:
        """Inject skill metadata into system prompt. Full content is loaded on-demand via skill tool."""
        skills = self.load_skills_metadata()
        if not skills:
            return event
        injected = "\n\n".join(
            f"## Skill: {s.name}\n**When to use:** {s.description}"
            for s in skills
        )
        new_prompt = event.system_prompt.rstrip() + "\n\n---\n# Available Skills\n\n" + injected
        return BeforeAgentStartEvent(system_prompt=new_prompt, messages=event.messages)
