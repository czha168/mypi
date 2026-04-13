from __future__ import annotations
import asyncio
import json
import logging
import re
from collections.abc import Callable
from typing import TYPE_CHECKING

from codepi.ai.provider import LLMProvider, TokenEvent, LLMToolCallEvent, DoneEvent
from codepi.core.events import (
    BeforeAgentStartEvent, BeforeProviderRequestEvent,
    ToolCallEvent, ToolResultEvent,
)
from codepi.core.session_manager import SessionManager, SessionEntry
from codepi.extensions.base import Extension
from codepi.extensions.skill_loader import SkillLoader
from codepi.tools.base import ToolRegistry, ToolResult, filter_tool_arguments

if TYPE_CHECKING:
    from codepi.core.security import SecurityMonitor
    from codepi.core.modes.plan_mode import PlanModeManager, PlanModeConfig
    from codepi.core.modes.auto_mode import AutoModeManager, AutoModeConfig

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = "You are a helpful coding assistant. Use the available tools to help the user."


def parse_tiered_response(raw: str) -> tuple[str, str]:
    l0 = ""
    l1 = ""
    abstract_match = re.search(
        r"ABSTRACT:\s*\n(.*?)(?=\n\s*\n\s*OVERVIEW:|\nOVERVIEW:|$)", raw, re.DOTALL | re.IGNORECASE,
    )
    overview_match = re.search(r"OVERVIEW:\s*\n(.*?)$", raw, re.DOTALL | re.IGNORECASE)
    if abstract_match:
        l0 = abstract_match.group(1).strip()
    if overview_match:
        l1 = overview_match.group(1).strip()
    if not l1:
        l1 = raw.strip()
    if not l0:
        first_sentence = re.split(r"[.!?]", l1, maxsplit=1)
        l0 = first_sentence[0].strip() if first_sentence else l1[:200]
    return l0, l1


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
        security_monitor: "SecurityMonitor | None" = None,
        on_security_ask: Callable[[str, str], bool] | None = None,
        plan_mode_manager: "PlanModeManager | None" = None,
        auto_mode_manager: "AutoModeManager | None" = None,
        on_mode_change: Callable[[str, str], None] | None = None,
        on_plan_approval: Callable[[str], bool] | None = None,
        on_auto_approval: Callable[[str, str], bool] | None = None,
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
        self._security_monitor = security_monitor
        self._on_security_ask = on_security_ask
        self._last_input_tokens: int = 0
        self._is_idle = True
        self._in_flight_tool: str | None = None
        self._steer_override: str | None = None

        # Mode managers
        self._plan_mode_manager = plan_mode_manager
        self._auto_mode_manager = auto_mode_manager
        self._on_mode_change = on_mode_change
        self._on_plan_approval = on_plan_approval
        self._on_auto_approval = on_auto_approval

        # Callbacks for callers (modes)
        self.on_token: Callable[[str], None] | None = None
        self.on_tool_call: Callable[[str, dict], None] | None = None
        self.on_tool_result: Callable[[str, ToolResult], None] | None = None
        self.on_error: Callable[[str], None] | None = None

    @property
    def is_idle(self) -> bool:
        return self._is_idle

    @property
    def current_mode(self) -> str:
        if self._plan_mode_manager and self._plan_mode_manager.is_active:
            return "plan"
        if self._auto_mode_manager and self._auto_mode_manager.is_active:
            return "auto"
        return "normal"

    @property
    def plan_phase(self) -> int | None:
        if self._plan_mode_manager and self._plan_mode_manager.is_active and self._plan_mode_manager.state:
            return self._plan_mode_manager.state.phase.value
        return None

    def start_plan_mode(self, user_request: str, plan_file: str | None = None) -> None:
        from codepi.core.modes.plan_mode import PlanModeManager
        if not self._plan_mode_manager:
            self._plan_mode_manager = PlanModeManager(
                on_phase_change=self._handle_phase_change,
                on_approval_required=self._handle_plan_approval,
            )
        from pathlib import Path
        self._plan_mode_manager.start(
            user_request,
            Path(plan_file) if plan_file else None,
        )
        if self._on_mode_change:
            self._on_mode_change("normal", "plan")

    def stop_plan_mode(self) -> None:
        if self._plan_mode_manager:
            self._plan_mode_manager.stop()
            if self._on_mode_change:
                self._on_mode_change("plan", "normal")

    def start_auto_mode(self) -> None:
        from codepi.core.modes.auto_mode import AutoModeManager, AutoModeConfig
        if not self._auto_mode_manager:
            self._auto_mode_manager = AutoModeManager(
                on_iteration_limit=self._handle_iteration_limit,
                on_approval_needed=self._handle_auto_approval,
            )
        self._auto_mode_manager.start()
        if self._on_mode_change:
            self._on_mode_change("normal", "auto")

    def stop_auto_mode(self) -> None:
        if self._auto_mode_manager:
            self._auto_mode_manager.stop()
            if self._on_mode_change:
                self._on_mode_change("auto", "normal")

    def _handle_phase_change(self, old_phase, new_phase) -> None:
        pass

    def _handle_plan_approval(self, design: str) -> bool:
        if self._on_plan_approval:
            return self._on_plan_approval(design)
        return False

    def _handle_iteration_limit(self, count: int) -> bool:
        return False

    def _handle_auto_approval(self, reason: str, operation: str) -> bool:
        if self._on_auto_approval:
            return self._on_auto_approval(reason, operation)
        return False

    def _is_edit_blocked_by_plan_mode(self, tool_name: str, arguments: dict) -> tuple[bool, str]:
        if not self._plan_mode_manager or not self._plan_mode_manager.is_active:
            return False, ""

        if tool_name not in ("write", "edit"):
            return False, ""

        state = self._plan_mode_manager.state
        if state is None:
            return False, ""

        file_path = arguments.get("file_path") or arguments.get("path")

        if state.is_edit_allowed(file_path):
            return False, ""

        return True, f"Plan mode active (phase {state.phase.name}) - edits not allowed"

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
                        retry_after = e.retry_after  # type: ignore[attr-defined]
        
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

                    tool_result = None
                    tool = self.tool_registry.get(call_evt.tool_name)
                    
                    # Check plan mode edit blocking
                    if tool_result is None:
                        blocked, reason = self._is_edit_blocked_by_plan_mode(
                            call_evt.tool_name, call_evt.arguments
                        )
                        if blocked:
                            tool_result = ToolResult(error=reason)
                    
                    # Check auto mode iteration limit
                    if tool_result is None and self._auto_mode_manager and self._auto_mode_manager.is_active:
                        can_continue, msg = self._auto_mode_manager.check_iteration_limit()
                        if not can_continue:
                            tool_result = ToolResult(error=f"Auto mode paused: {msg}")
                    
                    # Check auto mode approval gates
                    if tool_result is None and self._auto_mode_manager and self._auto_mode_manager.is_active:
                        from codepi.core.modes.auto_mode import get_sensitive_operation_from_command
                        operation = get_sensitive_operation_from_command(
                            call_evt.arguments.get("command", "")
                        ) if call_evt.tool_name == "bash" else None
                        approved, reason = self._auto_mode_manager.check_and_request_approval(
                            operation or call_evt.tool_name,
                            call_evt.tool_name,
                            call_evt.arguments,
                        )
                        if not approved:
                            tool_result = ToolResult(error=f"Auto mode approval required: {reason}")
                    
                    # Check security monitor
                    if self._security_monitor:
                        from codepi.core.security import SecurityAction
                        decision = self._security_monitor.evaluate_tool_call(
                            call_evt.tool_name,
                            call_evt.arguments,
                        )
                        
                        if decision.action == SecurityAction.BLOCK:
                            tool_result = ToolResult(error=f"Security: {decision.reason}")
                        elif decision.action == SecurityAction.ASK:
                            if self._on_security_ask:
                                approved = self._on_security_ask(decision.reason, decision.rule_id)
                                if not approved:
                                    tool_result = ToolResult(
                                        error=f"Security: Operation rejected by user - {decision.reason}"
                                    )
                            else:
                                tool_result = ToolResult(
                                    error=f"Security: {decision.reason} (requires approval)"
                                )
                    
                    if tool_result is None:
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
        context = self.session_manager.build_context()
        if not context:
            return
        tiered_prompt = [
            *context,
            {"role": "user", "content":
             "Summarize this conversation in two sections:\n\n"
             "ABSTRACT: A keyword/topic index in ~50 tokens listing key topics, "
             "file names, and decisions as a comma-separated list.\n\n"
             "OVERVIEW: A structured overview in ~500 tokens organized by topic, "
             "preserving all key decisions, file names, code changes, and technical details.\n\n"
             "Format your response as:\n"
             "ABSTRACT:\n<abstract here>\n\n"
             "OVERVIEW:\n<overview here>"},
        ]
        response_parts: list[str] = []
        async for event in self.provider.stream(
            messages=tiered_prompt, tools=[], model=self.model, system="",
        ):
            if isinstance(event, TokenEvent):
                response_parts.append(event.text)
        raw_response = "".join(response_parts)
        l0, l1 = parse_tiered_response(raw_response)
        self.session_manager.append(SessionEntry(
            type="tiered_compaction",
            data={"l0": l0, "l1": l1, "summary": l1},
        ))
        if self._memory_enabled():
            await self._run_memory_extraction(l1)

    def _memory_enabled(self) -> bool:
        try:
            from codepi.config import MemoryConfig
            return True
        except ImportError:
            return False

    async def _run_memory_extraction(self, l1_overview: str) -> None:
        try:
            from codepi.config import MemoryConfig
            from codepi.core.memory_store import MemoryStore
            from codepi.core.memory_extractor import MemoryExtractor
            from codepi.core.memory_dedup import MemoryDeduplicator
        except ImportError:
            return

        store = MemoryStore()
        extractor = MemoryExtractor()
        dedup = MemoryDeduplicator()
        dedup.index_existing(store)

        session_id = self.session_manager.session_id or ""
        candidates = await extractor.extract(l1_overview, session_id, self.provider, self.model)

        for candidate in candidates:
            result = dedup.check(candidate, store)
            if result.decision.value == "skip":
                if result.matched_id:
                    existing = store.get(result.matched_id)
                    if existing:
                        store.update(result.matched_id, access_count=existing.access_count + 1)
            elif result.decision.value == "merge":
                if result.matched_id:
                    existing = store.get(result.matched_id)
                    if existing:
                        merged = dedup.merge_content(existing.content, candidate.content)
                        store.update(result.matched_id, content=merged, access_count=existing.access_count + 1)
            else:
                store.add(candidate)

        store.enforce_capacity()
