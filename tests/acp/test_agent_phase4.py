import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from codepi.acp import CodepiAgent
from codepi.acp.session_adapter import ACPSessionAdapter
from codepi.config import Config, PathsConfig, ProviderConfig, SessionConfig, LSPConfig
from codepi.core.session_manager import SessionEntry, SessionManager


@pytest.fixture
def mock_config():
    return Config(
        provider=ProviderConfig(base_url="http://localhost:11434/v1", api_key="test", model="test-model"),
        session=SessionConfig(),
        paths=PathsConfig(sessions_dir=Path("/tmp/test-sessions")),
        lsp=LSPConfig(enabled=False),
    )


@pytest.fixture
def agent(mock_config):
    agent = CodepiAgent(mock_config)
    agent.on_connect(AsyncMock())
    return agent


@pytest.fixture
def mock_conn():
    conn = AsyncMock()
    conn.session_update = AsyncMock()
    return conn


@pytest.fixture
def adapter(mock_config, mock_conn):
    return ACPSessionAdapter(
        session_id="test-session-1",
        cwd="/tmp/project",
        config=mock_config,
        conn=mock_conn,
    )


def _make_session_with_entries(sessions_dir: Path, session_id: str, entries: list[SessionEntry]) -> None:
    sm = SessionManager(sessions_dir / session_id)
    sm.new_session(model="test-model")
    for entry in entries:
        sm.append(entry)


class TestListSessions:
    @pytest.mark.asyncio
    async def test_returns_session_ids(self, agent, mock_config, tmp_path):
        agent._config = Config(
            provider=ProviderConfig(base_url="http://localhost:11434/v1", api_key="test", model="test-model"),
            session=SessionConfig(),
            paths=PathsConfig(sessions_dir=tmp_path),
            lsp=LSPConfig(enabled=False),
        )
        sm = SessionManager(tmp_path)
        sm.new_session(model="test-model")

        resp = await agent.list_sessions()
        assert len(resp.sessions) >= 1
        assert resp.sessions[0].session_id == sm.session_id

    @pytest.mark.asyncio
    async def test_empty_sessions(self, agent, tmp_path):
        agent._config = Config(
            provider=ProviderConfig(base_url="http://localhost:11434/v1", api_key="test", model="test-model"),
            session=SessionConfig(),
            paths=PathsConfig(sessions_dir=tmp_path),
            lsp=LSPConfig(enabled=False),
        )
        resp = await agent.list_sessions()
        assert resp.sessions == []


class TestLoadSession:
    @pytest.mark.asyncio
    async def test_loads_session_and_replays(self, agent, mock_config, tmp_path, mock_conn):
        agent._config = Config(
            provider=ProviderConfig(base_url="http://localhost:11434/v1", api_key="test", model="test-model"),
            session=SessionConfig(),
            paths=PathsConfig(sessions_dir=tmp_path),
            lsp=LSPConfig(enabled=False),
        )
        agent._conn = mock_conn

        sm = SessionManager(tmp_path)
        sid = sm.new_session(model="test-model")
        sm.append(SessionEntry(type="message", data={"role": "user", "content": "hello"}))
        sm.append(SessionEntry(type="message", data={"role": "assistant", "content": "hi there"}))

        resp = await agent.load_session(cwd="/tmp", session_id=sid)

        assert resp is not None
        assert resp.modes is not None
        assert resp.modes.current_mode_id == "code"
        assert sid in agent._sessions

        assert mock_conn.session_update.await_count >= 2

    @pytest.mark.asyncio
    async def test_nonexistent_session_raises(self, agent, tmp_path):
        agent._config = Config(
            provider=ProviderConfig(base_url="http://localhost:11434/v1", api_key="test", model="test-model"),
            session=SessionConfig(),
            paths=PathsConfig(sessions_dir=tmp_path),
            lsp=LSPConfig(enabled=False),
        )
        with pytest.raises(ValueError, match="Session not found"):
            await agent.load_session(cwd="/tmp", session_id="nonexistent")


class TestCloseSession:
    @pytest.mark.asyncio
    async def test_removes_adapter(self, agent):
        resp = await agent.new_session(cwd="/tmp")
        sid = resp.session_id
        assert sid in agent._sessions

        result = await agent.close_session(session_id=sid)
        assert result is not None
        assert sid not in agent._sessions

    @pytest.mark.asyncio
    async def test_unknown_session_graceful(self, agent):
        result = await agent.close_session(session_id="nonexistent")
        assert result is not None


class TestForkSession:
    @pytest.mark.asyncio
    async def test_forks_session(self, agent, tmp_path, mock_conn):
        agent._config = Config(
            provider=ProviderConfig(base_url="http://localhost:11434/v1", api_key="test", model="test-model"),
            session=SessionConfig(),
            paths=PathsConfig(sessions_dir=tmp_path),
            lsp=LSPConfig(enabled=False),
        )
        agent._conn = mock_conn

        sm = SessionManager(tmp_path)
        sid = sm.new_session(model="test-model")
        sm.append(SessionEntry(type="message", data={"role": "user", "content": "hello"}))

        adapter = ACPSessionAdapter(session_id=sid, cwd="/tmp", config=agent._config, conn=mock_conn)
        adapter._setup_from_loaded_session(sm)
        agent._sessions[sid] = adapter

        result = await agent.fork_session(cwd="/tmp", session_id=sid)

        assert result.session_id != sid
        assert result.modes is not None
        assert result.session_id in agent._sessions

    @pytest.mark.asyncio
    async def test_unknown_session_raises(self, agent):
        with pytest.raises(ValueError, match="Session not found"):
            await agent.fork_session(cwd="/tmp", session_id="nonexistent")


class TestResumeSession:
    @pytest.mark.asyncio
    async def test_resumes_session(self, agent, tmp_path, mock_conn):
        agent._config = Config(
            provider=ProviderConfig(base_url="http://localhost:11434/v1", api_key="test", model="test-model"),
            session=SessionConfig(),
            paths=PathsConfig(sessions_dir=tmp_path),
            lsp=LSPConfig(enabled=False),
        )
        agent._conn = mock_conn

        sm = SessionManager(tmp_path)
        sid = sm.new_session(model="test-model")
        sm.append(SessionEntry(type="message", data={"role": "user", "content": "hello"}))

        result = await agent.resume_session(cwd="/tmp", session_id=sid)

        assert result is not None
        assert result.modes is not None
        assert sid in agent._sessions
        assert mock_conn.session_update.await_count == 0

    @pytest.mark.asyncio
    async def test_nonexistent_session_raises(self, agent, tmp_path):
        agent._config = Config(
            provider=ProviderConfig(base_url="http://localhost:11434/v1", api_key="test", model="test-model"),
            session=SessionConfig(),
            paths=PathsConfig(sessions_dir=tmp_path),
            lsp=LSPConfig(enabled=False),
        )
        with pytest.raises(ValueError, match="Session not found"):
            await agent.resume_session(cwd="/tmp", session_id="nonexistent")


class TestSetSessionMode:
    @pytest.mark.asyncio
    async def test_switch_to_plan(self, agent):
        resp = await agent.new_session(cwd="/tmp")
        sid = resp.session_id
        adapter = agent._sessions[sid]
        adapter._agent_session = MagicMock()

        result = await agent.set_session_mode(mode_id="plan", session_id=sid)
        assert result is not None
        adapter._agent_session.start_plan_mode.assert_called_once()
        assert adapter._current_mode_id == "plan"

    @pytest.mark.asyncio
    async def test_switch_to_auto(self, agent):
        resp = await agent.new_session(cwd="/tmp")
        sid = resp.session_id
        adapter = agent._sessions[sid]
        adapter._agent_session = MagicMock()

        await agent.set_session_mode(mode_id="auto", session_id=sid)
        adapter._agent_session.start_auto_mode.assert_called_once()
        assert adapter._current_mode_id == "auto"

    @pytest.mark.asyncio
    async def test_switch_to_code_from_plan(self, agent):
        resp = await agent.new_session(cwd="/tmp")
        sid = resp.session_id
        adapter = agent._sessions[sid]
        adapter._agent_session = MagicMock()
        adapter._current_mode_id = "plan"

        await agent.set_session_mode(mode_id="code", session_id=sid)
        adapter._agent_session.stop_plan_mode.assert_called_once()
        assert adapter._current_mode_id == "code"

    @pytest.mark.asyncio
    async def test_switch_to_code_from_auto(self, agent):
        resp = await agent.new_session(cwd="/tmp")
        sid = resp.session_id
        adapter = agent._sessions[sid]
        adapter._agent_session = MagicMock()
        adapter._current_mode_id = "auto"

        await agent.set_session_mode(mode_id="code", session_id=sid)
        adapter._agent_session.stop_auto_mode.assert_called_once()
        assert adapter._current_mode_id == "code"

    @pytest.mark.asyncio
    async def test_switch_to_ask(self, agent):
        resp = await agent.new_session(cwd="/tmp")
        sid = resp.session_id
        adapter = agent._sessions[sid]
        adapter._agent_session = MagicMock()

        await agent.set_session_mode(mode_id="ask", session_id=sid)
        assert adapter._current_mode_id == "ask"

    @pytest.mark.asyncio
    async def test_invalid_mode_raises(self, agent):
        resp = await agent.new_session(cwd="/tmp")
        sid = resp.session_id
        with pytest.raises(ValueError, match="Unknown mode"):
            await agent.set_session_mode(mode_id="unknown_mode", session_id=sid)

    @pytest.mark.asyncio
    async def test_unknown_session_raises(self, agent):
        with pytest.raises(ValueError, match="Session not found"):
            await agent.set_session_mode(mode_id="plan", session_id="nonexistent")

    @pytest.mark.asyncio
    async def test_mode_update_notification_sent(self, agent):
        resp = await agent.new_session(cwd="/tmp")
        sid = resp.session_id
        adapter = agent._sessions[sid]
        adapter._agent_session = MagicMock()

        await agent.set_session_mode(mode_id="plan", session_id=sid)
        agent._conn.session_update.assert_awaited_once()
        call_kwargs = agent._conn.session_update.call_args
        update = call_kwargs.kwargs["update"]
        assert update.current_mode_id == "plan"

    @pytest.mark.asyncio
    async def test_deferred_mode_on_uninitialized_session(self, agent):
        resp = await agent.new_session(cwd="/tmp")
        sid = resp.session_id
        adapter = agent._sessions[sid]
        assert adapter._agent_session is None

        await agent.set_session_mode(mode_id="auto", session_id=sid)
        assert adapter._pending_mode == "auto"


class TestSetSessionModel:
    @pytest.mark.asyncio
    async def test_update_on_initialized_session(self, agent):
        resp = await agent.new_session(cwd="/tmp")
        sid = resp.session_id
        adapter = agent._sessions[sid]
        adapter._agent_session = MagicMock()

        result = await agent.set_session_model(model_id="gpt-4o-mini", session_id=sid)
        assert result is not None
        assert adapter._agent_session.model == "gpt-4o-mini"

    @pytest.mark.asyncio
    async def test_deferred_on_uninitialized_session(self, agent):
        resp = await agent.new_session(cwd="/tmp")
        sid = resp.session_id
        adapter = agent._sessions[sid]
        assert adapter._agent_session is None

        result = await agent.set_session_model(model_id="gpt-4o-mini", session_id=sid)
        assert result is not None
        assert adapter._pending_model == "gpt-4o-mini"

    @pytest.mark.asyncio
    async def test_unknown_session_raises(self, agent):
        with pytest.raises(ValueError, match="Session not found"):
            await agent.set_session_model(model_id="gpt-4o-mini", session_id="nonexistent")


class TestExtMethod:
    @pytest.mark.asyncio
    async def test_memory_status(self, agent, tmp_path):
        agent._config = Config(
            provider=ProviderConfig(base_url="http://localhost:11434/v1", api_key="test", model="test-model"),
            session=SessionConfig(),
            paths=PathsConfig(sessions_dir=tmp_path),
            lsp=LSPConfig(enabled=False),
        )
        result = await agent.ext_method("_codepi/memory/status", {})
        assert "total_items" in result

    @pytest.mark.asyncio
    async def test_session_branches(self, agent, tmp_path, mock_conn):
        agent._config = Config(
            provider=ProviderConfig(base_url="http://localhost:11434/v1", api_key="test", model="test-model"),
            session=SessionConfig(),
            paths=PathsConfig(sessions_dir=tmp_path),
            lsp=LSPConfig(enabled=False),
        )
        agent._conn = mock_conn

        sm = SessionManager(tmp_path)
        sid = sm.new_session(model="test-model")

        adapter = ACPSessionAdapter(session_id=sid, cwd="/tmp", config=agent._config, conn=mock_conn)
        adapter._setup_from_loaded_session(sm)
        agent._sessions[sid] = adapter

        result = await agent.ext_method("_codepi/session/branches", {"session_id": sid})
        assert "leaf_ids" in result

    @pytest.mark.asyncio
    async def test_session_branches_unknown_session(self, agent):
        result = await agent.ext_method("_codepi/session/branches", {"session_id": "nonexistent"})
        assert result == {"leaf_ids": []}

    @pytest.mark.asyncio
    async def test_unknown_method_raises(self, agent):
        with pytest.raises(ValueError, match="Extension method not supported"):
            await agent.ext_method("_unknown/method", {})


class TestReplayHistory:
    @pytest.mark.asyncio
    async def test_replays_user_and_assistant(self, adapter, mock_conn):
        sm = MagicMock()
        sm.load_all_entries.return_value = [
            SessionEntry(type="message", data={"role": "user", "content": "hello"}),
            SessionEntry(type="message", data={"role": "assistant", "content": "hi there"}),
            SessionEntry(type="session_info", data={"version": 3}),
        ]
        adapter._loaded_session_manager = sm

        await adapter.replay_history()

        assert mock_conn.session_update.await_count == 2
        calls = mock_conn.session_update.call_args_list
        assert calls[0].kwargs["update"].content.text == "hello"
        assert calls[1].kwargs["update"].content.text == "hi there"

    @pytest.mark.asyncio
    async def test_skips_non_message_entries(self, adapter, mock_conn):
        sm = MagicMock()
        sm.load_all_entries.return_value = [
            SessionEntry(type="session_info", data={"version": 3}),
            SessionEntry(type="tiered_compaction", data={"l1": "summary"}),
        ]
        adapter._loaded_session_manager = sm

        await adapter.replay_history()
        mock_conn.session_update.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_empty_session(self, adapter, mock_conn):
        sm = MagicMock()
        sm.load_all_entries.return_value = []
        adapter._loaded_session_manager = sm

        await adapter.replay_history()
        mock_conn.session_update.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_no_loaded_session(self, adapter, mock_conn):
        adapter._loaded_session_manager = None
        await adapter.replay_history()
        mock_conn.session_update.assert_not_awaited()


class TestDeferredMode:
    @pytest.mark.asyncio
    async def test_pending_mode_applied_during_setup(self, adapter, mock_conn):
        adapter._pending_mode = "plan"
        adapter._loaded_session_manager = MagicMock()

        with patch.object(adapter, "_create_provider", return_value=MagicMock()), \
             patch.object(adapter, "_create_tool_registry", return_value=MagicMock()), \
             patch.object(adapter, "_load_extensions", return_value=[]), \
             patch("codepi.acp.session_adapter.AgentSession") as MockSession:
            mock_session = MagicMock()
            MockSession.return_value = mock_session
            await adapter._setup()

        mock_session.start_plan_mode.assert_called_once_with("")
        assert adapter._current_mode_id == "plan"
        assert adapter._pending_mode is None


class TestSetConfigOption:
    @pytest.mark.asyncio
    async def test_unknown_config_raises(self, agent):
        resp = await agent.new_session(cwd="/tmp")
        sid = resp.session_id
        adapter = agent._sessions[sid]
        adapter._agent_session = MagicMock()

        with pytest.raises(ValueError, match="Unknown config option"):
            await agent.set_config_option(config_id="unknown.option", session_id=sid, value="x")

    @pytest.mark.asyncio
    async def test_compaction_threshold(self, agent):
        resp = await agent.new_session(cwd="/tmp")
        sid = resp.session_id
        adapter = agent._sessions[sid]
        adapter._agent_session = MagicMock()

        result = await agent.set_config_option(config_id="compaction.threshold", session_id=sid, value="0.7")
        assert result is not None
        assert adapter._agent_session.compaction_threshold == 0.7
