import pytest
from unittest.mock import MagicMock
from codepi.modes.rpc import RPCMode
from codepi.core.session_manager import SessionManager


def make_mock_provider(events=None):
    p = MagicMock()
    return p


@pytest.mark.asyncio
async def test_rpc_mode_creates_agent(tmp_sessions_dir):
    provider = make_mock_provider()
    sm = SessionManager(tmp_sessions_dir)
    sm.new_session(model="gpt-4o")

    mode = RPCMode(provider=provider, session_manager=sm, model="gpt-4o")
    assert mode._config is not None


@pytest.mark.asyncio
async def test_rpc_mode_config_loaded(tmp_sessions_dir):
    provider = make_mock_provider()
    sm = SessionManager(tmp_sessions_dir)
    sm.new_session(model="gpt-4o")

    mode = RPCMode(provider=provider, session_manager=sm, model="gpt-4o")
    from codepi.config import Config
    assert isinstance(mode._config, Config)
