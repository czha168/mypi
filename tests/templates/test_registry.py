from pathlib import Path
from mypi.extensions.skill_loader import Skill
from mypi.templates.adapters import ClaudeAdapter, CursorAdapter, WindsurfAdapter, CommandContent
from mypi.templates.registry import TemplateRegistry


def test_claude_adapter_format():
    adapter = ClaudeAdapter()
    content = CommandContent(
        id="test-skill",
        name="mypi: Test Skill",
        description="A test skill",
        category="Workflow",
        tags=["test"],
        body="Do the thing.",
    )
    formatted = adapter.format_file(content)
    assert formatted.startswith("# mypi: Test Skill")
    assert "Do the thing." in formatted


def test_cursor_adapter_format():
    adapter = CursorAdapter()
    content = CommandContent(
        id="test-skill",
        name="mypi: Test Skill",
        description="A test skill",
        category="Workflow",
        tags=["test"],
        body="Do the thing.",
    )
    formatted = adapter.format_file(content)
    assert "name: mypi: Test Skill" in formatted
    assert "tags: test" in formatted
    assert "Do the thing." in formatted


def test_windsurf_adapter_format():
    adapter = WindsurfAdapter()
    content = CommandContent(
        id="test-skill",
        name="mypi: Test Skill",
        description="A test skill",
        category="Workflow",
        tags=["test"],
        body="Do the thing.",
    )
    formatted = adapter.format_file(content)
    assert formatted.startswith("mypi: Test Skill")
    assert "A test skill" in formatted
    assert "Do the thing." in formatted


def test_generate_commands_creates_files(tmp_path):
    skill_file = tmp_path / "test-skill.md"
    skill_file.write_text("""---
name: test-workflow
description: A test workflow skill
workflow: test-change
tags: [test]
category: Workflow
command_id: test-workflow
---

# mypi: Test Workflow

Do the test thing.
""")
    registry = TemplateRegistry([Path(tmp_path)])
    workflows = registry.load_workflows()
    assert "test-change" in workflows
    generated = registry.generate_commands("claude", Path(tmp_path))
    assert len(generated) == 1
    assert ".claude/commands/test-workflow.md" in str(generated[0])


def test_validate_parity_empty_body():
    registry = TemplateRegistry([])
    from mypi.templates.registry import WorkflowTemplate
    skill = Skill("empty-wf", "", Path("."), body=None)
    wf = WorkflowTemplate(skill=skill, command_id="empty-wf", command_tags=[], command_category="Test")
    registry._workflows = {"empty-wf": wf}
    errors = registry.validate_parity()
    assert any("empty skill body" in e for e in errors)
