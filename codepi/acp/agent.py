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
    ForkSessionResponse,
    Implementation,
    ListSessionsResponse,
    LoadSessionResponse,
    PromptCapabilities,
    ResumeSessionResponse,
    SessionMode,
    SessionModeState,
    SetSessionConfigOptionResponse,
    SetSessionModeResponse,
    SetSessionModelResponse,
)

from codepi.config import Config

__version__ = "0.1.0"

logger = logging.getLogger(__name__)


class CodepiAgent:
    """ACP Agent implementation for codepi.

    Satisfies the ``acp.Agent`` Protocol (structural typing).
    Phase 1 implements initialize, new_session, and on_connect.
    All other methods raise NotImplementedError for later phases.
    """

    def __init__(self, config: Config) -> None:
        self._config = config
        self._conn: Client | None = None
        self._sessions: dict[str, dict[str, Any]] = {}

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
        self._sessions[session_id] = {"cwd": cwd}
        return NewSessionResponse(
            session_id=session_id,
            modes=SessionModeState(
                available_modes=[
                    SessionMode(id="ask", name="Ask", description="Read-only Q&A"),
                    SessionMode(id="code", name="Code", description="Full tool access"),
                    SessionMode(id="plan", name="Plan", description="Structured planning workflow"),
                    SessionMode(id="auto", name="Auto", description="Continuous autonomous execution"),
                ],
                current_mode_id="code",
            ),
        )

    async def prompt(
        self,
        prompt: list[Any],
        session_id: str,
        message_id: str | None = None,
        **kwargs: Any,
    ) -> PromptResponse:
        raise NotImplementedError("Phase 2: session/prompt not yet implemented")

    async def cancel(self, session_id: str, **kwargs: Any) -> None:
        raise NotImplementedError("Phase 2: session/cancel not yet implemented")

    async def load_session(
        self, cwd: str, session_id: str, mcp_servers: list | None = None, **kwargs: Any
    ) -> LoadSessionResponse | None:
        raise NotImplementedError("Phase 4: session/load not yet implemented")

    async def list_sessions(
        self, cursor: str | None = None, cwd: str | None = None, **kwargs: Any
    ) -> ListSessionsResponse:
        raise NotImplementedError("Phase 4: session/list not yet implemented")

    async def close_session(self, session_id: str, **kwargs: Any) -> CloseSessionResponse | None:
        raise NotImplementedError("Phase 4: session/close not yet implemented")

    async def fork_session(
        self, cwd: str, session_id: str, mcp_servers: list | None = None, **kwargs: Any
    ) -> ForkSessionResponse:
        raise NotImplementedError("Phase 4: session/fork not yet implemented")

    async def resume_session(
        self, cwd: str, session_id: str, mcp_servers: list | None = None, **kwargs: Any
    ) -> ResumeSessionResponse:
        raise NotImplementedError("Phase 4: session/resume not yet implemented")

    async def set_session_mode(
        self, mode_id: str, session_id: str, **kwargs: Any
    ) -> SetSessionModeResponse | None:
        raise NotImplementedError("Phase 4: session/set_mode not yet implemented")

    async def set_session_model(
        self, model_id: str, session_id: str, **kwargs: Any
    ) -> SetSessionModelResponse | None:
        raise NotImplementedError("Phase 4: session/set_model not yet implemented")

    async def set_config_option(
        self, config_id: str, session_id: str, value: str | bool, **kwargs: Any
    ) -> SetSessionConfigOptionResponse | None:
        raise NotImplementedError("Phase 4: session/set_config_option not yet implemented")

    async def authenticate(self, method_id: str, **kwargs: Any) -> AuthenticateResponse | None:
        raise NotImplementedError("Phase 4: authenticate not yet implemented")

    async def ext_method(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError(f"Extension method not supported: {method}")

    async def ext_notification(self, method: str, params: dict[str, Any]) -> None:
        logger.warning("Ignoring unknown extension notification: %s", method)
