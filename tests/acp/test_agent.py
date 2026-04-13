import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from codepi.acp import CodepiAgent
from codepi.config import Config


@pytest.fixture
def agent():
    cfg = Config()
    agent = CodepiAgent(cfg)
    agent.on_connect(AsyncMock())
    return agent


@pytest.mark.asyncio
async def test_initialize_returns_correct_capabilities(agent):
    resp = await agent.initialize(protocol_version=1)
    data = resp.model_dump(by_alias=True)

    assert data["protocolVersion"] == 1
    assert data["agentCapabilities"]["loadSession"] is True
    assert data["agentCapabilities"]["promptCapabilities"]["image"] is False
    assert data["agentCapabilities"]["promptCapabilities"]["audio"] is False
    assert data["agentCapabilities"]["promptCapabilities"]["embeddedContext"] is True
    assert data["agentInfo"]["name"] == "codepi"
    assert data["agentInfo"]["title"] == "codepi"
    assert isinstance(data["agentInfo"]["version"], str) and len(data["agentInfo"]["version"]) > 0
    assert data["authMethods"] == []


@pytest.mark.asyncio
async def test_new_session_returns_uuid_and_four_modes(agent):
    resp = await agent.new_session(cwd="/tmp")
    data = resp.model_dump(by_alias=True)

    uuid.UUID(data["sessionId"])
    assert data["modes"]["currentModeId"] == "code"

    mode_ids = [m["id"] for m in data["modes"]["availableModes"]]
    assert mode_ids == ["ask", "code", "plan", "auto"]


@pytest.mark.asyncio
async def test_new_session_creates_adapter(agent):
    resp = await agent.new_session(cwd="/tmp")
    sid = resp.session_id
    assert sid in agent._sessions
    from codepi.acp.session_adapter import ACPSessionAdapter
    assert isinstance(agent._sessions[sid], ACPSessionAdapter)


@pytest.mark.asyncio
async def test_prompt_raises_valueerror_for_unknown_session(agent):
    with pytest.raises(ValueError, match="Unknown session"):
        await agent.prompt(prompt=[{"type": "text", "text": "hi"}], session_id="nonexistent")


@pytest.mark.asyncio
async def test_prompt_delegates_to_adapter(agent):
    resp = await agent.new_session(cwd="/tmp")
    sid = resp.session_id
    adapter = agent._sessions[sid]
    mock_response = MagicMock()
    adapter.run_prompt = AsyncMock(return_value=mock_response)

    result = await agent.prompt(prompt=[{"type": "text", "text": "hello"}], session_id=sid)

    adapter.run_prompt.assert_awaited_once_with([{"type": "text", "text": "hello"}])
    assert result is mock_response


@pytest.mark.asyncio
async def test_cancel_delegates_to_adapter(agent):
    resp = await agent.new_session(cwd="/tmp")
    sid = resp.session_id
    adapter = agent._sessions[sid]
    adapter.cancel = MagicMock()

    await agent.cancel(session_id=sid)
    adapter.cancel.assert_called_once()


@pytest.mark.asyncio
async def test_cancel_handles_unknown_session(agent):
    await agent.cancel(session_id="nonexistent")  # Should not raise


@pytest.mark.asyncio
async def test_on_connect_stores_connection(agent):
    mock_conn = object()
    agent.on_connect(mock_conn)
    assert agent._conn is mock_conn
