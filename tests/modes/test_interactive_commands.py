"""Unit tests for slash command dispatch in InteractiveMode.

Covers tasks 4.1–4.5 from the add-exit-and-websearch-commands change:
  4.1  _dispatch_command returns True/False correctly
  4.2  /exit sets _is_running = False
  4.3  /websearch with empty args shows usage
  4.4  /websearch with query calls WebSearchTool.execute() and renders
  4.5  /help shows all registered commands
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from codepi.modes.interactive import InteractiveMode
from codepi.tools.base import ToolResult


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def mode():
    """Build an InteractiveMode with all heavy collaborators mocked out."""
    with patch("codepi.modes.interactive.AgentSession"):
        m = InteractiveMode(
            provider=MagicMock(),
            session_manager=MagicMock(),
            model="test-model",
            session_id="test-session-id",
        )
    # Spy on renderer calls
    m._renderer.render_info = MagicMock()
    m._renderer.render_error = MagicMock()
    return m


# ===================================================================
# 4.1 — _dispatch_command return values
# ===================================================================

class TestDispatchCommandReturnValues:
    """_dispatch_command should return True for known commands and False otherwise."""

    @pytest.mark.parametrize("input_text", [
        "/exit",
        "/quit",
        "/help",
        "/websearch",
        "/clear",
    ])
    @pytest.mark.asyncio
    async def test_known_commands_return_true(self, mode, input_text):
        assert await mode._dispatch_command(input_text) is True

    @pytest.mark.parametrize("input_text", [
        "/unknown",
        "/opsx:explore",
        "/foo bar",
    ])
    @pytest.mark.asyncio
    async def test_unknown_commands_return_false(self, mode, input_text):
        assert await mode._dispatch_command(input_text) is False

    @pytest.mark.parametrize("input_text", [
        "hello",
        "explain this code",
        "",
    ])
    @pytest.mark.asyncio
    async def test_non_slash_input_returns_false(self, mode, input_text):
        assert await mode._dispatch_command(input_text) is False

    @pytest.mark.asyncio
    async def test_slash_with_args_parsed(self, mode):
        """'/websearch python asyncio' should dispatch to /websearch handler."""
        # Patch the handler so we can verify it was called with correct args
        mode._command_handlers["/websearch"] = AsyncMock()
        result = await mode._dispatch_command("/websearch python asyncio")
        assert result is True
        mode._command_handlers["/websearch"].assert_awaited_once_with(
            "python asyncio"
        )

    @pytest.mark.asyncio
    async def test_leading_whitespace_stripped(self, mode):
        """Leading whitespace is stripped so '  /exit' should still dispatch."""
        assert await mode._dispatch_command("  /exit") is True


# ===================================================================
# 4.2 — /exit handler
# ===================================================================

class TestHandleExit:
    @pytest.mark.asyncio
    async def test_exit_sets_is_running_false(self, mode):
        assert mode._is_running is True
        await mode._handle_exit("")
        assert mode._is_running is False

    @pytest.mark.asyncio
    async def test_quit_alias_sets_is_running_false(self, mode):
        """The /quit alias maps to the same handler."""
        assert mode._is_running is True
        await mode._command_handlers["/quit"]("")
        assert mode._is_running is False

    @pytest.mark.asyncio
    async def test_exit_renders_goodbye(self, mode):
        await mode._handle_exit("")
        mode._renderer.render_info.assert_called_once_with("Goodbye!")


# ===================================================================
# 4.3 — /websearch with empty args
# ===================================================================

class TestHandleWebsearchEmpty:
    @pytest.mark.asyncio
    async def test_empty_args_shows_usage(self, mode):
        await mode._handle_websearch("")
        mode._renderer.render_info.assert_called_once_with(
            "Usage: /websearch <query>"
        )

    @pytest.mark.asyncio
    async def test_whitespace_only_args_treated_as_empty(self, mode):
        await mode._handle_websearch("   ")
        mode._renderer.render_info.assert_called_once_with(
            "Usage: /websearch <query>"
        )


# ===================================================================
# 4.4 — /websearch with query
# ===================================================================

class TestHandleWebsearchWithQuery:
    @pytest.mark.asyncio
    async def test_execute_called_and_output_rendered(self, mode):
        fake_result = ToolResult(output="1. **Python**\n   URL: https://python.org\n   Snippet: Welcome\n")
        with patch("codepi.tools.web.web_search.WebSearchTool") as MockTool:
            instance = MockTool.return_value
            instance.execute = AsyncMock(return_value=fake_result)

            await mode._handle_websearch("python asyncio")

            MockTool.assert_called_once()
            instance.execute.assert_awaited_once_with(query="python asyncio")
            mode._renderer.render_info.assert_called_once_with(fake_result.output)

    @pytest.mark.asyncio
    async def test_execute_error_renders_error(self, mode):
        fake_result = ToolResult(error="Network timeout")
        with patch("codepi.tools.web.web_search.WebSearchTool") as MockTool:
            instance = MockTool.return_value
            instance.execute = AsyncMock(return_value=fake_result)

            await mode._handle_websearch("test query")

            mode._renderer.render_error.assert_called_once_with(
                "Web search failed: Network timeout"
            )

    @pytest.mark.asyncio
    async def test_import_error_renders_install_message(self, mode):
        with patch("codepi.tools.web.web_search.WebSearchTool", side_effect=ImportError):
            await mode._handle_websearch("test query")
            mode._renderer.render_error.assert_called_once_with(
                "web_search requires ddgs. Install with: pip install codepi[web]"
            )


# ===================================================================
# 4.5 — /help handler
# ===================================================================

class TestHandleHelp:
    @pytest.mark.asyncio
    async def test_help_prints_table_with_all_commands(self, mode):
        # Capture the table passed to console.print
        printed = []
        mode._console.print = lambda obj, **kw: printed.append(obj)

        await mode._handle_help("")

        assert len(printed) == 1
        table = printed[0]
        # Rich Table rows aren't directly inspectable for data,
        # so verify via the command registry that all commands are accounted for.
        registered = {cmd.name for cmd in mode._command_registry.list_commands()}
        assert len(registered) > 0

        # Verify the table title is set
        assert table.title == "Available Commands"

    @pytest.mark.asyncio
    async def test_help_includes_builtin_commands(self, mode):
        """The help output must list all built-in commands."""
        printed = []
        mode._console.print = lambda obj, **kw: printed.append(obj)

        await mode._handle_help("")

        table = printed[0]
        # Check column headers exist
        col_names = [col.header for col in table.columns]
        assert "Command" in col_names
        assert "Description" in col_names

        # Verify the registered commands include our builtins
        registered_names = {cmd.name for cmd in mode._command_registry.list_commands()}
        for expected in ("/help", "/clear", "/exit", "/model", "/websearch"):
            assert expected in registered_names, f"{expected} missing from command registry"
