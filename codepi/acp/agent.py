from __future__ import annotations

import logging
import uuid
from typing import Any

from acp import (
    Client,
    InitializeResponse,
    NewSessionResponse,
    PROTOCOL_VERSION,
    PromptResponse,
)
from acp.schema import (
    AgentCapabilities,
    AuthenticateResponse,
    CloseSessionResponse,
    CurrentModeUpdate,
    ForkSessionResponse,
    Implementation,
    ListSessionsResponse,
    LoadSessionResponse,
    PromptCapabilities,
    ResumeSessionResponse,
    SessionInfo,
    SessionMode,
    SessionModeState,
    SetSessionConfigOptionResponse,
    SetSessionModeResponse,
    SetSessionModelResponse,
)

from codepi.acp.session_adapter import ACPSessionAdapter
from codepi.config import Config
from codepi.core.session_manager import SessionManager

__version__ = "0.1.0"

logger = logging.getLogger(__name__)


_AVAILABLE_MODE_IDS = {"ask", "code", "plan", "auto"}


class CodepiAgent:
    """ACP Agent implementation for codepi.

    Satisfies the ``acp.Agent`` Protocol (structural typing).
    Phase 1 implements initialize, new_session, and on_connect.
    All other methods raise NotImplementedError for later phases.
    """

    def __init__(self, config: Config) -> None:
        self._config = config
        self._conn: Client | None = None
        self._sessions: dict[str, ACPSessionAdapter] = {}

    @staticmethod
    def _make_mode_state(current: str = "code") -> SessionModeState:
        return SessionModeState(
            available_modes=[
                SessionMode(id="ask", name="Ask", description="Read-only Q&A"),
                SessionMode(id="code", name="Code", description="Full tool access"),
                SessionMode(id="plan", name="Plan", description="Structured planning workflow"),
                SessionMode(id="auto", name="Auto", description="Continuous autonomous execution"),
            ],
            current_mode_id=current,
        )

    def on_connect(self, conn: Client) -> None:
        self._conn = conn

    async def initialize(
        self,
        protocol_version: int,
        client_capabilities: Any | None = None,
        client_info: Any | None = None,
        **kwargs: Any,
    ) -> InitializeResponse:
        return InitializeResponse(
            protocol_version=PROTOCOL_VERSION,
            agent_capabilities=AgentCapabilities(
                load_session=True,
                prompt_capabilities=PromptCapabilities(
                    image=False,
                    audio=False,
                    embedded_context=True,
                ),
            ),
            agent_info=Implementation(
                name="codepi",
                title="codepi",
                version=__version__,
            ),
            auth_methods=[],
        )

    async def new_session(
        self,
        cwd: str,
        mcp_servers: list | None = None,
        **kwargs: Any,
    ) -> NewSessionResponse:
        session_id = str(uuid.uuid4())
        self._sessions[session_id] = ACPSessionAdapter(
            session_id=session_id, cwd=cwd, config=self._config, conn=self._conn,  # type: ignore[arg-type]
        )
        return NewSessionResponse(
            session_id=session_id,
            modes=self._make_mode_state(),
        )

    async def prompt(
        self,
        prompt: list[Any],
        session_id: str,
        message_id: str | None = None,
        **kwargs: Any,
    ) -> PromptResponse:
        adapter = self._sessions.get(session_id)
        if adapter is None:
            raise ValueError(f"Unknown session: {session_id}")
        return await adapter.run_prompt(prompt)

    async def cancel(self, session_id: str, **kwargs: Any) -> None:
        adapter = self._sessions.get(session_id)
        if adapter is None:
            logger.warning("Cancel called for unknown session: %s", session_id)
            return
        adapter.cancel()

    async def load_session(
        self, cwd: str, session_id: str, mcp_servers: list | None = None, **kwargs: Any
    ) -> LoadSessionResponse | None:
        sm = SessionManager(self._config.paths.sessions_dir)
        try:
            sm.load_session(session_id)
        except FileNotFoundError:
            raise ValueError(f"Session not found: {session_id}")

        adapter = ACPSessionAdapter(
            session_id=session_id, cwd=cwd, config=self._config, conn=self._conn,  # type: ignore[arg-type]
        )
        adapter._setup_from_loaded_session(sm)
        self._sessions[session_id] = adapter
        await adapter.replay_history()
        return LoadSessionResponse(modes=self._make_mode_state(adapter._current_mode_id))

    async def list_sessions(
        self, cursor: str | None = None, cwd: str | None = None, **kwargs: Any
    ) -> ListSessionsResponse:
        session_ids = SessionManager.list_sessions(self._config.paths.sessions_dir)
        sessions = [SessionInfo(session_id=sid, cwd=cwd or "") for sid in session_ids]
        return ListSessionsResponse(sessions=sessions)

    async def close_session(self, session_id: str, **kwargs: Any) -> CloseSessionResponse | None:
        self._sessions.pop(session_id, None)
        return CloseSessionResponse()

    async def fork_session(
        self, cwd: str, session_id: str, mcp_servers: list | None = None, **kwargs: Any
    ) -> ForkSessionResponse:
        adapter = self._sessions.get(session_id)
        if adapter is None:
            raise ValueError(f"Session not found: {session_id}")

        sm = adapter._loaded_session_manager
        if sm is not None and sm.current_leaf_id:
            sm.branch(sm.current_leaf_id)

        new_id = str(uuid.uuid4())
        new_adapter = ACPSessionAdapter(
            session_id=new_id, cwd=cwd, config=self._config, conn=self._conn,  # type: ignore[arg-type]
        )
        if sm is not None:
            new_adapter._setup_from_loaded_session(sm)
        self._sessions[new_id] = new_adapter
        return ForkSessionResponse(session_id=new_id, modes=self._make_mode_state())

    async def resume_session(
        self, cwd: str, session_id: str, mcp_servers: list | None = None, **kwargs: Any
    ) -> ResumeSessionResponse:
        sm = SessionManager(self._config.paths.sessions_dir)
        try:
            sm.load_session(session_id)
        except FileNotFoundError:
            raise ValueError(f"Session not found: {session_id}")

        adapter = ACPSessionAdapter(
            session_id=session_id, cwd=cwd, config=self._config, conn=self._conn,  # type: ignore[arg-type]
        )
        adapter._setup_from_loaded_session(sm)
        self._sessions[session_id] = adapter
        return ResumeSessionResponse(modes=self._make_mode_state(adapter._current_mode_id))

    async def set_session_mode(
        self, mode_id: str, session_id: str, **kwargs: Any
    ) -> SetSessionModeResponse | None:
        adapter = self._sessions.get(session_id)
        if adapter is None:
            raise ValueError(f"Session not found: {session_id}")
        if mode_id not in _AVAILABLE_MODE_IDS:
            raise ValueError(f"Unknown mode: {mode_id}")

        adapter.set_mode(mode_id)
        await adapter._send_mode_update(mode_id)
        return SetSessionModeResponse()

    async def set_session_model(
        self, model_id: str, session_id: str, **kwargs: Any
    ) -> SetSessionModelResponse | None:
        adapter = self._sessions.get(session_id)
        if adapter is None:
            raise ValueError(f"Session not found: {session_id}")

        if adapter._agent_session is not None:
            adapter._agent_session.model = model_id
        else:
            adapter._pending_model = model_id
        return SetSessionModelResponse()

    async def set_config_option(
        self, config_id: str, session_id: str, value: str | bool, **kwargs: Any
    ) -> SetSessionConfigOptionResponse | None:
        adapter = self._sessions.get(session_id)
        if adapter is None:
            raise ValueError(f"Session not found: {session_id}")

        if config_id == "security.enabled":
            if adapter._agent_session is not None:
                monitor = adapter._agent_session._security_monitor
                if monitor is not None and monitor._config is not None:
                    monitor._config.enabled = bool(value)
        elif config_id == "compaction.threshold":
            if adapter._agent_session is not None:
                adapter._agent_session.compaction_threshold = float(value)
        else:
            raise ValueError(f"Unknown config option: {config_id}")
        return SetSessionConfigOptionResponse(config_options=[])

    async def authenticate(self, method_id: str, **kwargs: Any) -> AuthenticateResponse | None:
        return AuthenticateResponse()

    async def ext_method(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        if method == "_codepi/memory/status":
            from codepi.core.memory_store import MemoryStore
            store = MemoryStore(self._config.paths.sessions_dir.parent / "memories")
            return {"total_items": len(store.all_items)}

        if method == "_codepi/session/branches":
            session_id = params.get("session_id", "")
            adapter = self._sessions.get(session_id)
            if adapter is None or adapter._loaded_session_manager is None:
                return {"leaf_ids": []}
            return {"leaf_ids": adapter._loaded_session_manager.get_leaf_ids()}

        raise ValueError(f"Extension method not supported: {method}")

    async def ext_notification(self, method: str, params: dict[str, Any]) -> None:
        logger.warning("Ignoring unknown extension notification: %s", method)
