from __future__ import annotations

import asyncio
import logging
from typing import Literal

from acp import Client, PromptResponse
from acp.schema import (
    AgentMessageChunk,
    ContentToolCallContent,
    TextContentBlock,
    ToolCallLocation,
    ToolCallStart,
    ToolCallUpdate,
)

from codepi.acp.tool_adapter import (
    build_permission_options,
    extract_diff_content,
    extract_locations,
    map_tool_kind,
)
from codepi.ai.openai_compat import OpenAICompatProvider
from codepi.config import Config
from codepi.core.agent_session import AgentSession
from codepi.core.security import SecurityMonitor
from codepi.core.session_manager import SessionManager
from codepi.tools.builtins import make_builtin_registry

logger = logging.getLogger(__name__)

ToolKindType = Literal["read", "edit", "delete", "move", "search", "execute", "think", "fetch", "switch_mode", "other"]
StopReasonType = Literal["end_turn", "max_tokens", "max_turn_requests", "refusal", "cancelled"]


class ACPSessionAdapter:
    def __init__(
        self,
        session_id: str,
        cwd: str,
        config: Config,
        conn: Client,
    ) -> None:
        self.session_id = session_id
        self.cwd = cwd
        self.config = config
        self._conn = conn
        self._agent_session: AgentSession | None = None
        self._tool_call_counter: int = 0
        self._current_tool_call_id: str | None = None
        self._current_tool_name: str | None = None
        self._current_tool_arguments: dict = {}
        self._cancel_event: asyncio.Event = asyncio.Event()

    async def _setup(self) -> None:
        if self._agent_session is not None:
            return
        provider = self._create_provider()
        sm = SessionManager(self.config.paths.sessions_dir / self.session_id)
        sm.new_session(model=self.config.provider.model)
        registry = self._create_tool_registry()
        extensions = self._load_extensions()
        security_monitor = SecurityMonitor(self.config.security)
        self._agent_session = AgentSession(
            provider=provider,
            session_manager=sm,
            model=self.config.provider.model,
            tool_registry=registry,
            extensions=extensions,
            compaction_threshold=self.config.session.compaction_threshold,
            max_retries=self.config.session.max_retries,
            security_monitor=security_monitor,
            on_security_ask=self._on_security_ask,
        )
        self._agent_session.on_token = self._on_token
        self._agent_session.on_tool_call = self._on_tool_call
        self._agent_session.on_tool_result = self._on_tool_result
        self._agent_session.on_error = self._on_error

    async def _send_update(self, update) -> None:
        await self._conn.session_update(session_id=self.session_id, update=update)

    def _on_token(self, text: str) -> None:
        update = AgentMessageChunk(
            content=TextContentBlock(type="text", text=text),
            session_update="agent_message_chunk",
        )
        asyncio.create_task(self._send_update(update))

    def _on_tool_call(self, name: str, arguments: dict) -> None:
        self._tool_call_counter += 1
        self._current_tool_call_id = f"call_{self._tool_call_counter}"
        self._current_tool_name = name
        self._current_tool_arguments = arguments
        kind = map_tool_kind(name)
        locations = extract_locations(name, arguments)
        update = ToolCallStart(
            tool_call_id=self._current_tool_call_id,
            title=name,
            status="in_progress",
            kind=kind,  # type: ignore[arg-type]
            locations=locations,
            session_update="tool_call",
        )
        asyncio.create_task(self._send_update(update))

    def _on_tool_result(self, name: str, result) -> None:
        if self._current_tool_call_id is None:
            return
        has_error = result.error is not None if hasattr(result, "error") else isinstance(result, Exception)
        text = result.error if has_error else (result.output if hasattr(result, "output") else str(result))
        content: list = [ContentToolCallContent(content=TextContentBlock(type="text", text=text), type="content")]

        if not has_error:
            diff_content = extract_diff_content(name, self._current_tool_arguments, result)
            if diff_content:
                content.extend(diff_content)

        update = ToolCallUpdate(
            tool_call_id=self._current_tool_call_id,
            status="failed" if has_error else "completed",
            content=content,
        )
        asyncio.create_task(self._send_update(update))

    def _on_error(self, message: str) -> None:
        update = AgentMessageChunk(
            content=TextContentBlock(type="text", text=f"Error: {message}"),
            session_update="agent_message_chunk",
        )
        asyncio.create_task(self._send_update(update))

    async def _on_security_ask(self, reason: str, rule_id: str) -> bool:
        if self._current_tool_call_id is None:
            return False
        kind = map_tool_kind(self._current_tool_name or "")
        tool_call = ToolCallUpdate(
            tool_call_id=self._current_tool_call_id,
            kind=kind,  # type: ignore[arg-type]
            status="pending",
            title=f"Permission required: {reason}",
        )
        options = build_permission_options()
        try:
            response = await asyncio.wait_for(
                self._conn.request_permission(
                    options=options,
                    session_id=self.session_id,
                    tool_call=tool_call,
                ),
                timeout=120.0,
            )
            return response.outcome.outcome == "selected"
        except asyncio.TimeoutError:
            logger.warning("Permission request timed out for tool call %s", self._current_tool_call_id)
            return False

    def _create_provider(self):
        return OpenAICompatProvider(
            base_url=self.config.provider.base_url,
            api_key=self.config.provider.api_key,
            default_model=self.config.provider.model,
        )

    def _create_tool_registry(self):
        return make_builtin_registry(include_lsp=self.config.lsp.enabled)

    def _load_extensions(self):
        return []

    async def run_prompt(self, prompt_blocks: list[dict]) -> PromptResponse:
        await self._setup()
        self._cancel_event.clear()
        parts: list[str] = []
        for block in prompt_blocks:
            if block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif block.get("type") == "resource":
                res = block.get("resource", {})
                parts.append(res.get("text", ""))
        text = "\n".join(parts)
        try:
            await self._agent_session.prompt(text)  # type: ignore[union-attr]
            return PromptResponse(stop_reason="end_turn")
        except asyncio.CancelledError:
            return PromptResponse(stop_reason="cancelled")
        except Exception as e:
            logger.error("Prompt failed: %s", e)
            return PromptResponse(stop_reason="refusal")

    def cancel(self) -> None:
        self._cancel_event.set()
        if self._agent_session is not None:
            self._agent_session.cancel()
