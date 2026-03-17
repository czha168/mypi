import json
import pytest
import asyncio
from unittest.mock import MagicMock
from mypi.modes.rpc import RPCMode
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
async def test_rpc_mode_emits_token_jsonl(tmp_sessions_dir, capsys):
    provider = make_mock_provider([
        TokenEvent(text="Hello"),
        DoneEvent(usage=TokenUsage(10, 5)),
    ])
    sm = SessionManager(tmp_sessions_dir)
    sm.new_session(model="gpt-4o")

    stdin_data = json.dumps({"type": "prompt", "text": "hello"}) + "\n"
    stdin_data += json.dumps({"type": "exit"}) + "\n"
    stdin = asyncio.StreamReader()
    stdin.feed_data(stdin_data.encode())
    stdin.feed_eof()

    mode = RPCMode(provider=provider, session_manager=sm, model="gpt-4o")
    await mode.run(reader=stdin)

    captured = capsys.readouterr()
    lines = [l for l in captured.out.strip().split("\n") if l]
    types = [json.loads(l)["type"] for l in lines]
    assert "token" in types
    assert "done" in types
