from __future__ import annotations
import asyncio
import logging
from collections.abc import Callable
from mypi.ai.provider import LLMProvider, TokenEvent, LLMToolCallEvent, DoneEvent
from mypi.core.events import (
    BeforeAgentStartEvent, BeforeProviderRequestEvent,
    ToolCallEvent, ToolResultEvent,
    AutoRetryStartEvent, AutoRetryEndEvent,
    AutoCompactionStartEvent, AutoCompactionEndEvent,
)
from mypi.core.session_manager import SessionManager, SessionEntry
from mypi.extensions.base import Extension
from mypi.tools.base import ToolRegistry, ToolResult

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = "You are a helpful coding assistant. Use the available tools to help the user."


class AgentSession:
    def __init__(
        self,
        provider: LLMProvider,
        session_manager: SessionManager,
        model: str,
        tool_registry: ToolRegistry | None = None,
        extensions: list[Extension] | None = None,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        compaction_threshold: float = 0.80,
        max_retries: int = 3,
        context_window: int = 128_000,
    ):
        self.provider = provider
        self.session_manager = session_manager
        self.model = model
        self.tool_registry = tool_registry or ToolRegistry()
        self.extensions = extensions or []
        self.system_prompt = system_prompt
        self.compaction_threshold = compaction_threshold
        self.max_retries = max_retries
        self._context_window = context_window
        self._total_input_tokens: int = 0
        self._is_idle = True
        self._in_flight_tool: str | None = None
        self._steer_override: str | None = None

        # Callbacks for callers (modes)
        self.on_token: Callable[[str], None] | None = None
        self.on_tool_call: Callable[[str, dict], None] | None = None
        self.on_tool_result: Callable[[str, ToolResult], None] | None = None
        self.on_error: Callable[[str], None] | None = None

    @property
    def is_idle(self) -> bool:
        return self._is_idle

    async def prompt(self, text: str) -> None:
        self._is_idle = False
        try:
            self.session_manager.append(SessionEntry(type="message", data={"role": "user", "content": text}))
            await self._run_turn()
        finally:
            self._is_idle = True

    async def steer(self, text: str) -> None:
        """Inject a correction. If a tool call is in-flight, replaces its result.
        If no tool call is active, degrades to follow_up (queued as role: "user")."""
        if not self._is_idle and self._in_flight_tool:
            self._steer_override = text
        else:
            await self.follow_up(text)

    async def follow_up(self, text: str) -> None:
        await self.prompt(text)

    async def _run_turn(self) -> None:
        # Fire BeforeAgentStartEvent
        evt = BeforeAgentStartEvent(
            system_prompt=self.system_prompt,
            messages=self.session_manager.build_context(),
        )
        for ext in self.extensions:
            result = await ext.on_before_agent_start(evt)
            if result is not None:
                evt = result

        # Fire BeforeProviderRequestEvent
        params_evt = BeforeProviderRequestEvent(params={})
        for ext in self.extensions:
            result = await ext.on_before_provider_request(params_evt)
            if result is not None:
                params_evt = result

        for attempt in range(1, self.max_retries + 1):
            try:
                await self._stream_turn(evt, params_evt)
                return
            except Exception as e:
                if attempt >= self.max_retries:
                    if self.on_error:
                        self.on_error(f"Failed after {self.max_retries} attempts: {e}")
                    raise
                delay = 2 ** attempt
                logger.warning(f"Retrying (attempt {attempt}/{self.max_retries}) after {delay}s: {e}")
                await asyncio.sleep(delay)

    async def _stream_turn(self, start_evt: BeforeAgentStartEvent, params_evt: BeforeProviderRequestEvent) -> None:
        assistant_content = []
        tool_calls_made = []

        async for event in self.provider.stream(
            messages=start_evt.messages,
            tools=self.tool_registry.to_openai_schema(),
            model=self.model,
            system=start_evt.system_prompt,
            **params_evt.params,
        ):
            if isinstance(event, TokenEvent):
                assistant_content.append(event.text)
                if self.on_token:
                    self.on_token(event.text)

            elif isinstance(event, LLMToolCallEvent):
                call_evt = ToolCallEvent(tool_name=event.name, arguments=event.arguments)
                for ext in self.extensions:
                    result = await ext.on_tool_call(call_evt)
                    if result is not None:
                        call_evt = result

                if self.on_tool_call:
                    self.on_tool_call(call_evt.tool_name, call_evt.arguments)

                self._in_flight_tool = call_evt.tool_name
                self._steer_override = None

                tool = self.tool_registry.get(call_evt.tool_name)
                if tool:
                    tool_result = await tool.execute(**call_evt.arguments)
                else:
                    tool_result = ToolResult(error=f"Unknown tool: {call_evt.tool_name}")

                if self._steer_override is not None:
                    tool_result = ToolResult(output=self._steer_override)
                    self._steer_override = None

                self._in_flight_tool = None

                result_evt = ToolResultEvent(tool_name=call_evt.tool_name, result=tool_result)
                for ext in self.extensions:
                    r = await ext.on_tool_result(result_evt)
                    if r is not None:
                        result_evt = r

                if self.on_tool_result:
                    self.on_tool_result(result_evt.tool_name, result_evt.result)

                tool_calls_made.append({
                    "id": event.id,
                    "name": result_evt.tool_name,
                    "result": result_evt.result.to_message_content(),
                })

            elif isinstance(event, DoneEvent):
                self._total_input_tokens = event.usage.input_tokens
                if self._total_input_tokens > self._context_window * self.compaction_threshold:
                    await self._run_auto_compaction()

        # Persist assistant message
        if assistant_content:
            self.session_manager.append(SessionEntry(
                type="message",
                data={"role": "assistant", "content": "".join(assistant_content)},
            ))
        for tc in tool_calls_made:
            self.session_manager.append(SessionEntry(
                type="message",
                data={"role": "tool", "tool_call_id": tc["id"],
                      "name": tc["name"], "content": tc["result"]},
            ))

    async def _run_auto_compaction(self) -> None:
        """Summarize current context and store a CompactionEntry."""
        context = self.session_manager.build_context()
        if not context:
            return
        summary_prompt = [
            *context,
            {"role": "user", "content":
             "Please summarize the conversation so far in a concise paragraph, "
             "preserving all key decisions, file names, and code changes discussed."}
        ]
        summary_parts: list[str] = []
        async for event in self.provider.stream(
            messages=summary_prompt, tools=[], model=self.model, system=""
        ):
            if isinstance(event, TokenEvent):
                summary_parts.append(event.text)
        summary = "".join(summary_parts)
        self.session_manager.append(SessionEntry(
            type="compaction", data={"summary": summary}
        ))
