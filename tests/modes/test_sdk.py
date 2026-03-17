import pytest
from unittest.mock import MagicMock
from mypi.modes.sdk import SDK
from mypi.ai.provider import TokenEvent, DoneEvent, TokenUsage
from mypi.core.session_manager import SessionManager


def make_mock_provider(events):
    async def stream(*args, **kwargs):
        for e in events:
            yield e
    p = MagicMock()
    p.stream = stream
    return p


@pytest.mark.asyncio
async def test_sdk_prompt_returns_full_response(tmp_sessions_dir):
    provider = make_mock_provider([
        TokenEvent(text="The answer"),
        TokenEvent(text=" is 42"),
        DoneEvent(usage=TokenUsage(10, 5)),
    ])
    sm = SessionManager(tmp_sessions_dir)
    sm.new_session(model="gpt-4o")
    sdk = SDK(provider=provider, session_manager=sm, model="gpt-4o")
    response = await sdk.prompt("what is the answer?")
    assert "The answer" in response
    assert "42" in response


@pytest.mark.asyncio
async def test_sdk_stream_yields_tokens(tmp_sessions_dir):
    provider = make_mock_provider([
        TokenEvent(text="chunk1"),
        TokenEvent(text="chunk2"),
        DoneEvent(usage=TokenUsage(5, 3)),
    ])
    sm = SessionManager(tmp_sessions_dir)
    sm.new_session(model="gpt-4o")
    sdk = SDK(provider=provider, session_manager=sm, model="gpt-4o")
    chunks = []
    async for chunk in sdk.stream("hello"):
        chunks.append(chunk)
    assert "chunk1" in chunks
    assert "chunk2" in chunks
