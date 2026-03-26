import pytest
from io import StringIO
from unittest.mock import MagicMock
from codepi.modes.print_mode import PrintMode
from codepi.ai.provider import TokenEvent, DoneEvent, TokenUsage
from codepi.core.session_manager import SessionManager


def make_mock_provider(events):
    async def stream(*args, **kwargs):
        for e in events:
            yield e
    p = MagicMock()
    p.stream = stream
    return p


@pytest.mark.asyncio
async def test_print_mode_outputs_tokens_to_stdout(tmp_sessions_dir):
    provider = make_mock_provider([
        TokenEvent(text="Hello"),
        TokenEvent(text=", world"),
        DoneEvent(usage=TokenUsage(10, 5)),
    ])
    sm = SessionManager(tmp_sessions_dir)
    sm.new_session(model="gpt-4o")

    output = StringIO()
    mode = PrintMode(provider=provider, session_manager=sm, model="gpt-4o", output=output)
    await mode.run("say hello")

    result = output.getvalue()
    assert "Hello" in result
    assert ", world" in result


@pytest.mark.asyncio
async def test_print_mode_shows_tool_calls(tmp_sessions_dir):
    from codepi.ai.provider import LLMToolCallEvent
    from codepi.tools.base import Tool, ToolResult, ToolRegistry

    class EchoTool(Tool):
        name = "echo"; description = "echo"
        input_schema = {"type": "object", "properties": {"text": {"type": "string"}}}
        async def execute(self, text=""): return ToolResult(output=text)

    registry = ToolRegistry()
    registry.register(EchoTool())

    call_count = 0
    async def provider_stream(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            yield LLMToolCallEvent(id="c1", name="echo", arguments={"text": "hi"})
            yield DoneEvent(usage=TokenUsage(10, 5))
        else:
            yield TokenEvent(text="Tool result: ")
            yield DoneEvent(usage=TokenUsage(50, 10))

    provider = MagicMock()
    provider.stream = provider_stream
    sm = SessionManager(tmp_sessions_dir)
    sm.new_session(model="gpt-4o")

    output = StringIO()
    mode = PrintMode(provider=provider, session_manager=sm, model="gpt-4o",
                     tool_registry=registry, output=output)
    await mode.run("use echo")
    assert "echo" in output.getvalue()
