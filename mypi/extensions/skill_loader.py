from __future__ import annotations
from pathlib import Path
import yaml
from mypi.core.events import BeforeAgentStartEvent


def _parse_skill(path: Path) -> dict | None:
    """Parse a Claude Code–format skill .md file. Returns dict with name, description, body."""
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
        body = text[close_idx + 4:].strip()  # skip "\n---"
        if not isinstance(frontmatter, dict) or "name" not in frontmatter:
            return None
        return {"name": frontmatter["name"], "description": frontmatter.get("description", ""),
                "compatibility": frontmatter.get("compatibility"), "body": body}
    except Exception:
        return None


class SkillLoader:
    def __init__(self, skills_dirs: list[Path]):
        self.skills_dirs = [Path(d) for d in skills_dirs]

    def load_skills(self) -> list[dict]:
        skills = []
        for d in self.skills_dirs:
            if not d.exists():
                continue
            for md_file in sorted(d.glob("*.md")):
                skill = _parse_skill(md_file)
                if skill:
                    skills.append(skill)
        return skills

    def inject_skills(self, event: BeforeAgentStartEvent) -> BeforeAgentStartEvent:
        skills = self.load_skills()
        if not skills:
            return event
        injected = "\n\n".join(
            f"## Skill: {s['name']}\n**When to use:** {s['description']}\n\n{s['body']}"
            for s in skills
        )
        new_prompt = event.system_prompt.rstrip() + "\n\n---\n# Available Skills\n\n" + injected
        return BeforeAgentStartEvent(system_prompt=new_prompt, messages=event.messages)
