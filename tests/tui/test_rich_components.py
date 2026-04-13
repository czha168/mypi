import pytest
from unittest.mock import patch, MagicMock
from codepi.core.commands import CommandRegistry, Command
from codepi.tui.rich_components import RichInput


class TestRichInputWithoutRegistry:
    def test_no_prompt_session_without_registry(self):
        inp = RichInput()
        assert inp._prompt_session is None

    def test_uses_console_input_without_registry(self):
        inp = RichInput()
        with patch.object(inp.console, "input", return_value="hello"):
            result = inp._get_input_sync(MagicMock())
            assert result == "hello"


class TestRichInputWithRegistry:
    def test_creates_prompt_session_with_registry(self):
        reg = CommandRegistry()
        reg.register(Command(name="/help", description="Show help"))
        inp = RichInput(command_registry=reg)
        assert inp._prompt_session is not None

    def test_prompt_session_has_completer(self):
        reg = CommandRegistry()
        reg.register(Command(name="/help"))
        inp = RichInput(command_registry=reg)
        assert inp._prompt_session is not None
        assert inp._prompt_session.completer is not None

    def test_prompt_session_complete_while_typing(self):
        reg = CommandRegistry()
        inp = RichInput(command_registry=reg)
        assert inp._prompt_session is not None
        assert inp._prompt_session.complete_while_typing is True
