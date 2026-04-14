import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from codepi.acp.session_adapter import ACPSessionAdapter
from codepi.acp.tool_adapter import extract_diff_content, extract_locations, map_tool_kind


@pytest.fixture
def mock_conn():
    conn = AsyncMock()
    conn.session_update = AsyncMock()
    return conn


@pytest.fixture
def mock_config():
    from codepi.config import Config, ProviderConfig, PathsConfig, SessionConfig, LSPConfig
    from pathlib import Path
    return Config(
        provider=ProviderConfig(base_url="http://localhost:11434/v1", api_key="test", model="test-model"),
        session=SessionConfig(),
        paths=PathsConfig(sessions_dir=Path("/tmp/test-sessions")),
        lsp=LSPConfig(enabled=False),
    )


@pytest.fixture
def adapter(mock_config, mock_conn):
    return ACPSessionAdapter(
        session_id="test-session-1",
        cwd="/tmp/project",
        config=mock_config,
        conn=mock_conn,
    )


class TestMapToolKind:
    def test_known_tools(self):
        expected = {
            "read": "read", "write": "edit", "edit": "edit", "bash": "execute",
            "find": "search", "grep": "search", "ls": "read",
            "lsp_diagnostics": "read", "lsp_goto_definition": "read",
            "lsp_find_references": "search", "lsp_hover": "read", "lsp_rename": "edit",
        }
        for tool_name, expected_kind in expected.items():
            assert map_tool_kind(tool_name) == expected_kind, (
                f"Expected {tool_name} -> {expected_kind}"
            )

    def test_unknown_tool_returns_other(self):
        assert map_tool_kind("custom_tool") == "other"
        assert map_tool_kind("unknown") == "other"


class TestExtractLocations:
    def test_file_path_argument(self):
        result = extract_locations("edit", {"file_path": "/tmp/main.py"})
        assert result is not None
        assert len(result) == 1
        assert result[0].path == "/tmp/main.py"

    def test_path_argument(self):
        result = extract_locations("read", {"path": "/tmp/config.toml"})
        assert result is not None
        assert len(result) == 1
        assert result[0].path == "/tmp/config.toml"

    def test_no_path_argument(self):
        result = extract_locations("bash", {"command": "ls"})
        assert result is None

    def test_file_path_takes_priority(self):
        result = extract_locations("edit", {"file_path": "/a.py", "path": "/b.py"})
        assert result is not None
        assert result[0].path == "/a.py"


class TestOnToken:
    @pytest.mark.asyncio
    async def test_sends_agent_message_chunk(self, adapter, mock_conn):
        adapter._on_token("Hello")
        await asyncio.sleep(0)
        mock_conn.session_update.assert_awaited_once()
        call_kwargs = mock_conn.session_update.call_args
        assert call_kwargs.kwargs["session_id"] == "test-session-1"
        update = call_kwargs.kwargs["update"]
        assert update.content.text == "Hello"


class TestOnToolCall:
    @pytest.mark.asyncio
    async def test_increments_counter_and_sends_notification(self, adapter, mock_conn):
        adapter._on_tool_call("read", {"path": "/tmp/file.py"})
        assert adapter._tool_call_counter == 1
        assert adapter._current_tool_call_id == "call_1"
        assert adapter._current_tool_name == "read"
        assert adapter._current_tool_arguments == {"path": "/tmp/file.py"}

        adapter._on_tool_call("bash", {"command": "ls"})
        assert adapter._tool_call_counter == 2
        assert adapter._current_tool_call_id == "call_2"


class TestOnToolResult:
    @pytest.mark.asyncio
    async def test_completed_status(self, adapter, mock_conn):
        adapter._current_tool_call_id = "call_1"
        adapter._current_tool_name = "read"
        adapter._current_tool_arguments = {"path": "/tmp/file.py"}
        from codepi.tools.base import ToolResult
        result = ToolResult(output="file contents")
        adapter._on_tool_result("read", result)

    @pytest.mark.asyncio
    async def test_failed_status(self, adapter, mock_conn):
        adapter._current_tool_call_id = "call_1"
        adapter._current_tool_name = "read"
        adapter._current_tool_arguments = {"path": "/tmp/file.py"}
        from codepi.tools.base import ToolResult
        result = ToolResult(error="file not found")
        adapter._on_tool_result("read", result)

    def test_skips_without_current_id(self, adapter, mock_conn):
        adapter._current_tool_call_id = None
        from codepi.tools.base import ToolResult
        adapter._on_tool_result("read", ToolResult(output="ok"))

    @pytest.mark.asyncio
    async def test_edit_tool_includes_diff_content(self, adapter, mock_conn):
        adapter._current_tool_call_id = "call_1"
        adapter._current_tool_name = "edit"
        adapter._current_tool_arguments = {"file_path": "/tmp/main.py", "old_string": "old", "new_string": "new"}
        from codepi.tools.base import ToolResult
        result = ToolResult(output="OK")
        adapter._on_tool_result("edit", result)
        await asyncio.sleep(0)
        mock_conn.session_update.assert_awaited_once()
        call_kwargs = mock_conn.session_update.call_args
        update = call_kwargs.kwargs["update"]
        assert update.status == "completed"
        assert len(update.content) == 2
        diff = update.content[1]
        assert diff.type == "diff"
        assert diff.path == "/tmp/main.py"
        assert diff.old_text == "old"
        assert diff.new_text == "new"

    @pytest.mark.asyncio
    async def test_write_tool_includes_diff_content(self, adapter, mock_conn):
        adapter._current_tool_call_id = "call_1"
        adapter._current_tool_name = "write"
        adapter._current_tool_arguments = {"file_path": "/tmp/new.py", "content": "print('hello')"}
        from codepi.tools.base import ToolResult
        result = ToolResult(output="OK")
        adapter._on_tool_result("write", result)
        await asyncio.sleep(0)
        mock_conn.session_update.assert_awaited_once()
        call_kwargs = mock_conn.session_update.call_args
        update = call_kwargs.kwargs["update"]
        assert update.status == "completed"
        assert len(update.content) == 2
        diff = update.content[1]
        assert diff.type == "diff"
        assert diff.path == "/tmp/new.py"
        assert diff.old_text is None
        assert diff.new_text == "print('hello')"

    @pytest.mark.asyncio
    async def test_bash_tool_no_diff_content(self, adapter, mock_conn):
        adapter._current_tool_call_id = "call_1"
        adapter._current_tool_name = "bash"
        adapter._current_tool_arguments = {"command": "ls"}
        from codepi.tools.base import ToolResult
        result = ToolResult(output="file1.py\nfile2.py")
        adapter._on_tool_result("bash", result)
        await asyncio.sleep(0)
        mock_conn.session_update.assert_awaited_once()
        call_kwargs = mock_conn.session_update.call_args
        update = call_kwargs.kwargs["update"]
        assert update.status == "completed"
        assert len(update.content) == 1


class TestOnError:
    @pytest.mark.asyncio
    async def test_sends_error_message(self, adapter, mock_conn):
        adapter._on_error("Rate limited")


class TestCancel:
    def test_sets_cancel_event(self, adapter):
        assert not adapter._cancel_event.is_set()
        adapter.cancel()
        assert adapter._cancel_event.is_set()

    def test_calls_agent_session_cancel(self, adapter):
        mock_session = MagicMock()
        adapter._agent_session = mock_session
        adapter.cancel()
        mock_session.cancel.assert_called_once()

    def test_handles_no_session(self, adapter):
        adapter._agent_session = None
        adapter.cancel()
