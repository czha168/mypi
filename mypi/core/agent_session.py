from __future__ import annotations
import asyncio
import json
import logging
from collections.abc import Callable
from mypi.ai.provider import LLMProvider, TokenEvent, LLMToolCallEvent, DoneEvent
from mypi.core.events import (
    BeforeAgentStartEvent, BeforeProviderRequestEvent,
    ToolCallEvent, ToolResultEvent,
)
from mypi.core.session_manager import SessionManager, SessionEntry
from mypi.extensions.base import Extension
from mypi.extensions.skill_loader import SkillLoader
from mypi.tools.base import ToolRegistry, ToolResult, filter_tool_arguments

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
        skill_loader: SkillLoader | None = None,
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
        self._skill_loader = skill_loader
        self._last_input_tokens: int = 0
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

    def _is_opsx_command(self, text: str) -> bool:
        stripped = text.strip()
        return stripped.startswith("/opsx:") and len(stripped) > 6

    def _handle_opsx_command(self, text: str) -> str:
        prefix = "/opsx:"
        rest = text.strip()[len(prefix):]
        if " " in rest:
            command, args = rest.split(" ", 1)
        else:
            command, args = rest, ""
        skill_name = f"opsx-{command}"
        if self._skill_loader:
            skill = self._skill_loader.load_skill_content(skill_name)
            if skill and skill.body:
                return (
                    f"--- Skill: {skill.name} ---\n\n"
                    f"{skill.body}\n\n"
                    f"--- User Request ---\n\n{args}"
                )
        return text

    async def prompt(self, text: str) -> None:
        if not self._is_idle:
            raise RuntimeError("Cannot prompt while a turn is already in progress")
        self._is_idle = False
        try:
            if self._is_opsx_command(text):
                text = self._handle_opsx_command(text)
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

        for attempt in range(self.max_retries):
            try:
                await self._stream_turn(evt, params_evt)
                return
            except Exception as e:
                if attempt == self.max_retries - 1:
                    # Max retries exhausted - save recovery checkpoint
                    retry_after = 60  # default
                    if hasattr(e, 'retry_after'):
                        retry_after = e.retry_after
        
                    reason = f"Rate limited after {self.max_retries} attempts: {str(e)}"
                    self.session_manager.save_recovery_checkpoint(reason, retry_after)
        
                    if self.on_error:
                        self.on_error(
                            f"Max retries ({self.max_retries}) exhausted. "
                            f"Session saved. Retry in {retry_after}s: {e}"
                        )
                    raise
                delay = 2 ** attempt
                logger.warning(f"Retrying (attempt {attempt + 1}/{self.max_retries}) after {delay}s: {e}")
                await asyncio.sleep(delay)

    async def _stream_turn(self, start_evt: BeforeAgentStartEvent, params_evt: BeforeProviderRequestEvent) -> None:
        # Messages to send to LLM - start with context
        messages = list(start_evt.messages)
        assistant_content: list[str] = []
        pending_assistant_msg: dict | None = None

        while True:
            tool_calls_this_round: list[dict] = []
            tool_results: list[dict] = []

            async for event in self.provider.stream(
                messages=messages,
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
                    # Track tool call in assistant message
                    if pending_assistant_msg is None:
                        pending_assistant_msg = {
                            "role": "assistant",
                            "content": "",
                            "tool_calls": []
                        }
                    pending_assistant_msg["tool_calls"].append({
                        "id": event.id,
                        "type": "function",
                        "function": {
                            "name": event.name,
                            "arguments": ""
                        }
                    })
                    # Accumulate function arguments (may come in multiple chunks)
                    # Find and update the tool_call
                    for tc in pending_assistant_msg["tool_calls"]:
                        if tc["id"] == event.id:
                            tc["function"]["arguments"] += json.dumps(event.arguments) if event.arguments else ""

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
                        filtered_args = filter_tool_arguments(tool, call_evt.arguments)
                        tool_result = await tool.execute(**filtered_args)
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

                    tool_results.append({
                        "role": "tool",
                        "tool_call_id": event.id,
                        "content": result_evt.result.to_message_content(),
                    })

                elif isinstance(event, DoneEvent):
                    self._last_input_tokens = event.usage.input_tokens

            # If we had tool calls, append them and continue
            if pending_assistant_msg and tool_results:
                # Complete the pending assistant message
                pending_assistant_msg["content"] = "".join(assistant_content)
                messages.append(pending_assistant_msg)
                messages.extend(tool_results)
                # Reset for next round
                assistant_content = []
                pending_assistant_msg = None
                # Continue loop to get next response from LLM
                continue

            # No more tool calls - we're done
            break

        # Persist assistant message
        if assistant_content or pending_assistant_msg:
            if pending_assistant_msg:
                pending_assistant_msg["content"] = "".join(assistant_content)
                msg_content = pending_assistant_msg["content"]
            else:
                msg_content = "".join(assistant_content)
            self.session_manager.append(SessionEntry(
                type="message",
                data={"role": "assistant", "content": msg_content},
            ))

        # Check compaction after the final response
        if self._last_input_tokens > self._context_window * self.compaction_threshold:
            await self._run_auto_compaction()

    # AutoCompactionStartEvent/AutoCompactionEndEvent are dispatched by TUI layer
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
