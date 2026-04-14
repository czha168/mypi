import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from acp.schema import AllowedOutcome, DeniedOutcome, RequestPermissionResponse
from codepi.acp.session_adapter import ACPSessionAdapter
from codepi.tools.base import ToolResult


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
def mock_conn():
    conn = AsyncMock()
    conn.session_update = AsyncMock()
    conn.request_permission = AsyncMock()
    return conn


@pytest.fixture
def adapter(mock_config, mock_conn):
    return ACPSessionAdapter(
        session_id="test-session-1",
        cwd="/tmp/project",
        config=mock_config,
        conn=mock_conn,
    )


def _allowed_response():
    return RequestPermissionResponse(
        outcome=AllowedOutcome(option_id="allow_once", outcome="selected"),
    )


def _denied_response():
    return RequestPermissionResponse(
        outcome=DeniedOutcome(outcome="cancelled"),
    )


class TestOnSecurityAsk:
    @pytest.mark.asyncio
    async def test_allowed_returns_true(self, adapter, mock_conn):
        mock_conn.request_permission.return_value = _allowed_response()
        adapter._current_tool_call_id = "call_1"
        adapter._current_tool_name = "bash"
        result = await adapter._on_security_ask("Pushing to remote. Confirm?", "shared:push")
        assert result is True
        mock_conn.request_permission.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_denied_returns_false(self, adapter, mock_conn):
        mock_conn.request_permission.return_value = _denied_response()
        adapter._current_tool_call_id = "call_1"
        adapter._current_tool_name = "bash"
        result = await adapter._on_security_ask("Pushing to remote. Confirm?", "shared:push")
        assert result is False

    @pytest.mark.asyncio
    async def test_timeout_returns_false(self, adapter, mock_conn):
        mock_conn.request_permission.side_effect = asyncio.TimeoutError()
        adapter._current_tool_call_id = "call_1"
        adapter._current_tool_name = "bash"
        result = await adapter._on_security_ask("Pushing to remote. Confirm?", "shared:push")
        assert result is False

    @pytest.mark.asyncio
    async def test_no_current_tool_call_returns_false(self, adapter, mock_conn):
        adapter._current_tool_call_id = None
        result = await adapter._on_security_ask("reason", "rule_id")
        assert result is False
        mock_conn.request_permission.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_sends_permission_options(self, adapter, mock_conn):
        mock_conn.request_permission.return_value = _allowed_response()
        adapter._current_tool_call_id = "call_1"
        adapter._current_tool_name = "bash"
        await adapter._on_security_ask("Pushing to remote?", "shared:push")
        call_kwargs = mock_conn.request_permission.call_args
        options = call_kwargs.kwargs["options"]
        assert len(options) == 4
        kinds = [o.kind for o in options]
        assert kinds == ["allow_once", "allow_always", "reject_once", "reject_always"]

    @pytest.mark.asyncio
    async def test_sends_tool_call_context(self, adapter, mock_conn):
        mock_conn.request_permission.return_value = _allowed_response()
        adapter._current_tool_call_id = "call_3"
        adapter._current_tool_name = "bash"
        await adapter._on_security_ask("Pushing to remote?", "shared:push")
        call_kwargs = mock_conn.request_permission.call_args
        tool_call = call_kwargs.kwargs["tool_call"]
        assert tool_call.tool_call_id == "call_3"
        assert tool_call.kind == "execute"
        assert tool_call.status == "pending"


class TestPermissionFlowIntegration:
    @pytest.mark.asyncio
    async def test_bash_push_triggers_permission(self, adapter, mock_conn):
        mock_conn.request_permission.return_value = _allowed_response()
        adapter._current_tool_call_id = "call_1"
        adapter._current_tool_name = "bash"
        adapter._current_tool_arguments = {"command": "git push"}

        approved = await adapter._on_security_ask("Pushing to remote. Confirm?", "shared:push")
        assert approved is True
        mock_conn.request_permission.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_edit_tool_result_with_diff(self, adapter, mock_conn):
        adapter._current_tool_call_id = "call_1"
        adapter._current_tool_name = "edit"
        adapter._current_tool_arguments = {
            "file_path": "/tmp/main.py",
            "old_string": "old code",
            "new_string": "new code",
        }
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
        assert diff.old_text == "old code"
        assert diff.new_text == "new code"

    @pytest.mark.asyncio
    async def test_write_tool_result_with_diff(self, adapter, mock_conn):
        adapter._current_tool_call_id = "call_1"
        adapter._current_tool_name = "write"
        adapter._current_tool_arguments = {
            "file_path": "/tmp/new.py",
            "content": "print('hello')",
        }
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
    async def test_edit_tool_error_no_diff(self, adapter, mock_conn):
        adapter._current_tool_call_id = "call_1"
        adapter._current_tool_name = "edit"
        adapter._current_tool_arguments = {
            "file_path": "/tmp/main.py",
            "old_string": "x",
            "new_string": "y",
        }
        result = ToolResult(error="old_string not found")
        adapter._on_tool_result("edit", result)
        await asyncio.sleep(0)
        mock_conn.session_update.assert_awaited_once()
        call_kwargs = mock_conn.session_update.call_args
        update = call_kwargs.kwargs["update"]
        assert update.status == "failed"
        assert len(update.content) == 1
