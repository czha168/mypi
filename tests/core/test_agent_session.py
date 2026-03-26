import pytest
from unittest.mock import AsyncMock, MagicMock
from codepi.core.agent_session import AgentSession
from codepi.ai.provider import TokenEvent, LLMToolCallEvent, DoneEvent, TokenUsage
from codepi.core.session_manager import SessionManager
from codepi.tools.builtins import make_builtin_registry


def make_mock_provider(events):
    """Create a mock LLMProvider that yields the given events."""
    async def stream(*args, **kwargs):
        for e in events:
            yield e
    provider = MagicMock()
    provider.stream = stream
    return provider


@pytest.mark.asyncio
async def test_prompt_fires_token_events(tmp_sessions_dir):
    events = [TokenEvent(text="Hello"), TokenEvent(text=" world"), DoneEvent(usage=TokenUsage(10, 5))]
    provider = make_mock_provider(events)
    sm = SessionManager(tmp_sessions_dir)
    sm.new_session(model="gpt-4o")
    session = AgentSession(provider=provider, session_manager=sm, model="gpt-4o")

    received_tokens = []
    session.on_token = lambda t: received_tokens.append(t)

    await session.prompt("say hello")
    assert received_tokens == ["Hello", " world"]


@pytest.mark.asyncio
async def test_prompt_executes_tool_calls(tmp_sessions_dir):
    call_count = 0
    
    async def provider_stream(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # First call: LLM requests tool call
            yield LLMToolCallEvent(id="c1", name="echo", arguments={"text": "from tool"})
            yield DoneEvent(usage=TokenUsage(10, 5))
        else:
            # Second call: LLM continues after tool result
            yield TokenEvent(text="Tool result received: ")
            yield DoneEvent(usage=TokenUsage(50, 10))
    
    from codepi.tools.base import Tool, ToolResult, ToolRegistry
    class EchoTool(Tool):
        name = "echo"
        description = "echo"
        input_schema = {"type": "object", "properties": {"text": {"type": "string"}}}
        async def execute(self, text=""):
            return ToolResult(output=text)

    registry = ToolRegistry()
    registry.register(EchoTool())
    
    provider = MagicMock()
    provider.stream = provider_stream
    sm = SessionManager(tmp_sessions_dir)
    sm.new_session(model="gpt-4o")
    session = AgentSession(provider=provider, session_manager=sm, model="gpt-4o", tool_registry=registry)

    tool_results = []
    session.on_tool_result = lambda name, result: tool_results.append((name, result))

    await session.prompt("use echo")
    assert any(r[0] == "echo" and r[1].output == "from tool" for r in tool_results)
    assert call_count == 2  # Should make 2 calls: initial + after tool result


@pytest.mark.asyncio
async def test_prompt_stores_messages_in_session(tmp_sessions_dir):
    events = [TokenEvent(text="Hi"), DoneEvent(usage=TokenUsage(5, 3))]
    provider = make_mock_provider(events)
    sm = SessionManager(tmp_sessions_dir)
    sm.new_session(model="gpt-4o")
    session = AgentSession(provider=provider, session_manager=sm, model="gpt-4o")

    await session.prompt("hello")
    ctx = sm.build_context()
    assert any(m.get("content") == "hello" for m in ctx)


from unittest.mock import patch


@pytest.mark.asyncio
async def test_prompt_retries_on_api_error(tmp_sessions_dir):
    call_count = 0

    async def flaky_stream(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise Exception("server error")
        yield TokenEvent(text="ok")
        yield DoneEvent(usage=TokenUsage(5, 3))

    provider = MagicMock()
    provider.stream = flaky_stream
    sm = SessionManager(tmp_sessions_dir)
    sm.new_session(model="gpt-4o")
    session = AgentSession(provider=provider, session_manager=sm, model="gpt-4o", max_retries=3)

    with patch("asyncio.sleep", new_callable=AsyncMock):
        await session.prompt("test")

    assert call_count == 3


@pytest.mark.asyncio
async def test_prompt_raises_after_max_retries(tmp_sessions_dir):
    async def always_fail(*args, **kwargs):
        raise Exception("always fails")
        yield  # make it an async generator

    provider = MagicMock()
    provider.stream = always_fail
    sm = SessionManager(tmp_sessions_dir)
    sm.new_session(model="gpt-4o")

    errors_received = []
    session = AgentSession(provider=provider, session_manager=sm, model="gpt-4o", max_retries=2)
    session.on_error = lambda msg: errors_received.append(msg)

    with patch("asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(Exception, match="always fails"):
            await session.prompt("fail")

    assert len(errors_received) == 1
    assert "always fails" in errors_received[0]


@pytest.mark.asyncio
async def test_compaction_runs_when_threshold_exceeded(tmp_sessions_dir):
    """When DoneEvent reports token usage > threshold, auto-compaction should fire."""
    call_count = 0

    async def provider_stream(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            yield TokenEvent(text="answer")
            yield DoneEvent(usage=TokenUsage(input_tokens=110_000, output_tokens=500))
        else:
            yield TokenEvent(text="Summary of prior context.")
            yield DoneEvent(usage=TokenUsage(input_tokens=1000, output_tokens=100))

    provider = MagicMock()
    provider.stream = provider_stream
    sm = SessionManager(tmp_sessions_dir)
    sm.new_session(model="gpt-4o")
    session = AgentSession(provider=provider, session_manager=sm, model="gpt-4o",
                           compaction_threshold=0.80)

    await session.prompt("heavy request")

    entries = sm.load_all_entries()
    compaction_entries = [e for e in entries if e.type == "compaction"]
    assert len(compaction_entries) == 1
    assert "Summary" in compaction_entries[0].data.get("summary", "")
