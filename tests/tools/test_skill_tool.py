import pytest
from codepi.extensions.skill_loader import SkillLoader
from codepi.tools.skill_tool import SkillTool


def write_skill(skills_dir, name, content):
    (skills_dir / f"{name}.md").write_text(content)


@pytest.fixture
def skill_loader(tmp_skills_dir):
    write_skill(tmp_skills_dir, "commit-message", """---
name: commit-message
description: Use when writing git commit messages.
---

When writing commits:
1. Use imperative mood
2. Keep subject line under 50 chars
""")
    return SkillLoader(skills_dirs=[tmp_skills_dir])


@pytest.mark.asyncio
async def test_skill_tool_loads_content(skill_loader):
    tool = SkillTool(skill_loader_getter=lambda: skill_loader)
    result = await tool.execute(name="commit-message")
    assert result.error is None
    assert "Use imperative mood" in result.output
    assert "Keep subject line" in result.output


@pytest.mark.asyncio
async def test_skill_tool_not_found(skill_loader):
    tool = SkillTool(skill_loader_getter=lambda: skill_loader)
    result = await tool.execute(name="nonexistent")
    assert result.error is not None
    assert "not found" in result.error


@pytest.mark.asyncio
async def test_skill_tool_no_loader():
    tool = SkillTool(skill_loader_getter=lambda: None)
    result = await tool.execute(name="anything")
    assert result.error == "No skill loader configured"
