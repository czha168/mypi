import pytest

from codepi.acp.tool_adapter import (
    build_permission_options,
    extract_diff_content,
    extract_locations,
    map_tool_kind,
    should_request_permission,
)
from codepi.core.security import SecurityAction, SecurityDecision
from codepi.tools.base import ToolResult


class TestMapToolKind:
    def test_known_tools(self):
        assert map_tool_kind("read") == "read"
        assert map_tool_kind("write") == "edit"
        assert map_tool_kind("edit") == "edit"
        assert map_tool_kind("bash") == "execute"
        assert map_tool_kind("grep") == "search"

    def test_unknown_tool(self):
        assert map_tool_kind("custom") == "other"


class TestExtractLocations:
    def test_file_path(self):
        result = extract_locations("edit", {"file_path": "/tmp/a.py"})
        assert result is not None
        assert result[0].path == "/tmp/a.py"

    def test_path(self):
        result = extract_locations("read", {"path": "/tmp/b.py"})
        assert result is not None
        assert result[0].path == "/tmp/b.py"

    def test_no_path(self):
        assert extract_locations("bash", {"command": "ls"}) is None


class TestExtractDiffContent:
    def test_edit_tool_successful(self):
        result = extract_diff_content(
            "edit",
            {"file_path": "/tmp/main.py", "old_string": "old code", "new_string": "new code"},
            ToolResult(output="OK"),
        )
        assert result is not None
        assert len(result) == 1
        assert result[0].type == "diff"
        assert result[0].path == "/tmp/main.py"
        assert result[0].old_text == "old code"
        assert result[0].new_text == "new code"

    def test_write_tool_successful(self):
        result = extract_diff_content(
            "write",
            {"file_path": "/tmp/new.py", "content": "print('hello')"},
            ToolResult(output="OK"),
        )
        assert result is not None
        assert len(result) == 1
        assert result[0].type == "diff"
        assert result[0].path == "/tmp/new.py"
        assert result[0].old_text is None
        assert result[0].new_text == "print('hello')"

    def test_bash_tool_returns_none(self):
        result = extract_diff_content(
            "bash",
            {"command": "ls"},
            ToolResult(output="file1.py"),
        )
        assert result is None

    def test_read_tool_returns_none(self):
        result = extract_diff_content(
            "read",
            {"path": "/tmp/a.py"},
            ToolResult(output="contents"),
        )
        assert result is None

    def test_edit_tool_with_error_returns_none(self):
        result = extract_diff_content(
            "edit",
            {"file_path": "/tmp/a.py", "old_string": "x", "new_string": "y"},
            ToolResult(error="old_string not found"),
        )
        assert result is None

    def test_write_tool_with_error_returns_none(self):
        result = extract_diff_content(
            "write",
            {"file_path": "/tmp/a.py", "content": "new"},
            ToolResult(error="permission denied"),
        )
        assert result is None


class TestShouldRequestPermission:
    def test_ask_decision_returns_true(self):
        decision = SecurityDecision(action=SecurityAction.ASK, reason="test", rule_id="test:rule")
        assert should_request_permission("bash", {"command": "git push"}, decision) is True

    def test_allow_decision_returns_false(self):
        decision = SecurityDecision(action=SecurityAction.ALLOW, reason="safe")
        assert should_request_permission("bash", {"command": "ls"}, decision) is False

    def test_block_decision_returns_false(self):
        decision = SecurityDecision(action=SecurityAction.BLOCK, reason="dangerous")
        assert should_request_permission("bash", {"command": "rm -rf /"}, decision) is False


class TestBuildPermissionOptions:
    def test_returns_four_options(self):
        options = build_permission_options()
        assert len(options) == 4

    def test_option_kinds(self):
        options = build_permission_options()
        kinds = [o.kind for o in options]
        assert kinds == ["allow_once", "allow_always", "reject_once", "reject_always"]

    def test_option_names(self):
        options = build_permission_options()
        names = [o.name for o in options]
        assert "Allow once" in names
        assert "Allow always" in names
        assert "Reject once" in names
        assert "Reject always" in names
