from __future__ import annotations

import logging

from acp import run_agent

from codepi.acp.agent import CodepiAgent
from codepi.ai.provider import LLMProvider
from codepi.config import Config, load_config
from codepi.core.session_manager import SessionManager
from codepi.extensions.skill_loader import SkillLoader
from codepi.tools.base import ToolRegistry

logger = logging.getLogger(__name__)


class RPCMode:
    """RPC mode using the Agent Client Protocol (ACP) JSON-RPC 2.0 transport.

    Accepts the same constructor signature as other modes for CLI
    compatibility, but delegates all wire-protocol handling to the
    ACP SDK's ``run_agent()`` entry point.
    """

    def __init__(
        self,
        provider: LLMProvider,
        session_manager: SessionManager,
        model: str,
        tool_registry: ToolRegistry | None = None,
        extensions: list | None = None,
        skill_loader: SkillLoader | None = None,
    ) -> None:
        self._config: Config = load_config()

    async def run(self, reader=None) -> None:  # noqa: ARG002 – reader param kept for API compat
        """Start the ACP JSON-RPC transport over stdio."""
        agent = CodepiAgent(config=self._config)
        await run_agent(agent)
