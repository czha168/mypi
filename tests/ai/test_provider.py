import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from codepi.ai.provider import LLMProvider, TokenEvent, LLMToolCallEvent, DoneEvent, TokenUsage


def test_provider_event_types():
    tok = TokenEvent(text="hello")
    tool = LLMToolCallEvent(id="c1", name="read", arguments={"path": "x"})
    done = DoneEvent(usage=TokenUsage(input_tokens=100, output_tokens=50))
    assert tok.text == "hello"
    assert tool.name == "read"
    assert done.usage.input_tokens == 100


def test_llm_provider_is_abstract():
    import inspect
    assert inspect.isabstract(LLMProvider)


# --- OpenAICompatProvider tests ---
from codepi.ai.openai_compat import OpenAICompatProvider


@pytest.mark.asyncio
async def test_openai_compat_streams_tokens():
    provider = OpenAICompatProvider(base_url="http://localhost", api_key="test", default_model="gpt-4o")

    # Mock the openai client stream - must be an async iterator
    chunk1 = MagicMock()
    chunk1.choices = [MagicMock(delta=MagicMock(content="Hello", tool_calls=None))]
    chunk1.usage = None

    final_chunk = MagicMock()
    final_chunk.choices = [MagicMock(delta=MagicMock(content=None, tool_calls=None))]
    final_chunk.usage = MagicMock(prompt_tokens=10, completion_tokens=5)

    # Create an async iterator from the chunks
    async def async_iter():
        yield chunk1
        yield final_chunk

    mock_stream = async_iter()

    with patch.object(provider._client.chat.completions, "create", return_value=mock_stream):
        events = []
        async for event in provider.stream(messages=[], tools=[], model="gpt-4o", system=""):
            events.append(event)

    token_events = [e for e in events if isinstance(e, TokenEvent)]
    done_events = [e for e in events if isinstance(e, DoneEvent)]
    assert any(e.text == "Hello" for e in token_events)
    assert len(done_events) == 1


@pytest.mark.asyncio
async def test_openai_compat_emits_tool_call():
    provider = OpenAICompatProvider(base_url="http://localhost", api_key="test", default_model="gpt-4o")

    tool_chunk = MagicMock()
    tool_call = MagicMock()
    tool_call.index = 0
    tool_call.id = "call_abc"
    tool_call.function.name = "read"
    tool_call.function.arguments = '{"path": "foo.py"}'
    tool_chunk.choices = [MagicMock(delta=MagicMock(content=None, tool_calls=[tool_call]), finish_reason="tool_calls")]
    tool_chunk.usage = None

    final_chunk = MagicMock()
    final_chunk.choices = [MagicMock(delta=MagicMock(content=None, tool_calls=None), finish_reason=None)]
    final_chunk.usage = MagicMock(prompt_tokens=20, completion_tokens=10)

    async def async_iter():
        yield tool_chunk
        yield final_chunk

    mock_stream = async_iter()

    with patch.object(provider._client.chat.completions, "create", return_value=mock_stream):
        events = []
        async for event in provider.stream(messages=[], tools=[], model="gpt-4o", system=""):
            events.append(event)

    tool_events = [e for e in events if isinstance(e, LLMToolCallEvent)]
    assert len(tool_events) == 1
    assert tool_events[0].name == "read"
