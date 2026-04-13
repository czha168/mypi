import uuid

import pytest

from codepi.acp import CodepiAgent
from codepi.config import Config


@pytest.fixture
def agent():
    return CodepiAgent(Config())


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
async def test_prompt_raises_not_implemented(agent):
    with pytest.raises(NotImplementedError, match="Phase 2"):
        await agent.prompt(prompt=[], session_id="x")


@pytest.mark.asyncio
async def test_on_connect_stores_connection(agent):
    mock_conn = object()
    agent.on_connect(mock_conn)
    assert agent._conn is mock_conn
