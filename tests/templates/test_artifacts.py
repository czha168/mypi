"""Tests for OpenSpec artifact templates."""

from mypi.templates.artifacts import TEMPLATES, ARTIFACT_DIR


def test_templates_contains_all_artifacts():
    assert "proposal" in TEMPLATES
    assert "spec" in TEMPLATES
    assert "design" in TEMPLATES
    assert "tasks" in TEMPLATES


def test_templates_count():
    assert len(TEMPLATES) == 4


def test_proposal_template_has_required_sections():
    content = TEMPLATES["proposal"]
    assert "## Why" in content
    assert "## What Changes" in content
    assert "## Capabilities" in content
    assert "### New Capabilities" in content
    assert "### Modified Capabilities" in content
    assert "## Impact" in content


def test_spec_template_has_delta_sections():
    content = TEMPLATES["spec"]
    assert "## ADDED Requirements" in content
    assert "## MODIFIED Requirements" in content
    assert "## REMOVED Requirements" in content
    assert "#### Scenario:" in content
    assert "**WHEN**" in content
    assert "**THEN**" in content


def test_design_template_has_required_sections():
    content = TEMPLATES["design"]
    assert "## Context" in content
    assert "## Goals / Non-Goals" in content
    assert "## Decisions" in content
    assert "## Risks / Trade-offs" in content
    assert "## Migration Plan" in content


def test_tasks_template_has_checkbox_format():
    content = TEMPLATES["tasks"]
    assert "- [ ]" in content
    assert "## 1." in content
    assert "## 2." in content


def test_all_templates_non_empty():
    for key, value in TEMPLATES.items():
        assert value.strip(), f"Template '{key}' is empty"
        assert len(value) > 100, f"Template '{key}' is suspiciously short"


def test_artifact_files_match_templates(tmp_path):
    """Verify artifact files on disk match TEMPLATES dict."""
    for name, content in TEMPLATES.items():
        expected_file = ARTIFACT_DIR / f"{name}.md"
        assert expected_file.exists(), f"Missing artifact file: {expected_file}"
        assert expected_file.read_text() == content, f"Template dict out of sync with {name}.md"
