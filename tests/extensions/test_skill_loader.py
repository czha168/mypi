import pytest
from pathlib import Path
from mypi.extensions.skill_loader import SkillLoader
from mypi.core.events import BeforeAgentStartEvent


def write_skill(skills_dir: Path, name: str, content: str):
    (skills_dir / f"{name}.md").write_text(content)


@pytest.fixture
def skill_with_frontmatter(tmp_skills_dir):
    write_skill(tmp_skills_dir, "my-skill", """---
name: my-skill
description: Use when the user asks about Python.
---

## My Skill

Always use type hints.
""")
    return tmp_skills_dir


def test_skill_loader_injects_metadata_only(skill_with_frontmatter):
    """Skills are injected with metadata only; full content loads on-demand."""
    loader = SkillLoader(skills_dirs=[skill_with_frontmatter])
    evt = BeforeAgentStartEvent(system_prompt="Base prompt.", messages=[])
    modified = loader.inject_skills(evt)
    assert "my-skill" in modified.system_prompt
    assert "Use when the user asks about Python" in modified.system_prompt
    assert "Always use type hints" not in modified.system_prompt


def test_skill_loader_loads_full_content_on_demand(skill_with_frontmatter):
    """load_skill_content returns full body when requested."""
    loader = SkillLoader(skills_dirs=[skill_with_frontmatter])
    skill = loader.load_skill_content("my-skill")
    assert skill is not None
    assert skill.name == "my-skill"
    assert skill.body is not None
    assert "Always use type hints" in skill.body


def test_skill_loader_ignores_invalid_frontmatter(tmp_skills_dir):
    write_skill(tmp_skills_dir, "bad-skill", "No frontmatter here.")
    loader = SkillLoader(skills_dirs=[tmp_skills_dir])
    evt = BeforeAgentStartEvent(system_prompt="Base.", messages=[])
    modified = loader.inject_skills(evt)
    assert modified.system_prompt == "Base."


def test_skill_loader_scans_multiple_dirs(tmp_path):
    dir1 = tmp_path / "d1"
    dir2 = tmp_path / "d2"
    dir1.mkdir(); dir2.mkdir()
    write_skill(dir1, "skill-a", "---\nname: skill-a\ndescription: A.\n---\nContent A")
    write_skill(dir2, "skill-b", "---\nname: skill-b\ndescription: B.\n---\nContent B")
    loader = SkillLoader(skills_dirs=[dir1, dir2])
    metadata = loader.load_skills_metadata()
    assert len(metadata) == 2
    names = {s.name for s in metadata}
    assert "skill-a" in names
    assert "skill-b" in names
