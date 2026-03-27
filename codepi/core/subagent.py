"""Subagent framework for spawning specialized agents."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from codepi.ai.provider import LLMProvider
    from codepi.core.session_manager import SessionManager
    from codepi.tools.base import ToolRegistry, ToolResult


logger = logging.getLogger(__name__)


class SubagentStatus(Enum):
    """Status of subagent execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class SubagentConfig:
    """Configuration for a subagent."""
    
    name: str
    system_prompt: str
    tools: list[str]  # Tool names (whitelist)
    read_only: bool = False
    max_turns: int = 10
    timeout_seconds: float = 300.0
    extra_params: dict[str, Any] = field(default_factory=dict)


@dataclass
class SubagentResult:
    """Result from subagent execution."""
    
    status: SubagentStatus
    output: str = ""
    error: str | None = None
    tool_calls: list[dict] = field(default_factory=list)
    tokens_used: int = 0


class ReadOnlyBashFilter:
    """Filters bash commands to only allow read-only operations."""
    
    READ_ONLY_COMMANDS = {
        "ls", "cat", "head", "tail", "find", "grep", "rg", "ag",
        "git status", "git log", "git diff", "git show", "git branch",
        "git remote", "git rev-parse", "git ls-files", "git ls-tree",
        "pwd", "echo", "which", "type", "env", "printenv",
        "stat", "file", "wc", "sort", "uniq", "cut", "awk", "sed",
    }
    
    BLOCKED_PATTERNS = [
        # Destructive
        r"\brm\s+-rf\b",
        r"\brm\s+-r\b",
        r"\brm\s*-.*f\b",
        r"\bDROP\s+TABLE\b",
        r"\bDELETE\s+FROM\b",
        r"\bTRUNCATE\b",
        r"\bkill\s+-9\b",
        # File modifications
        r"\bmkdir\b",
        r"\btouch\b",
        r"\bcp\b",
        r"\bmv\b",
        r"\bchmod\b",
        r"\bchown\b",
        # Git modifications
        r"\bgit\s+add\b",
        r"\bgit\s+commit\b",
        r"\bgit\s+push\b",
        r"\bgit\s+reset\b",
        r"\bgit\s+checkout\b",
        r"\bgit\s+rebase\b",
        r"\bgit\s+merge\b",
        # Package managers
        r"\bnpm\s+install\b",
        r"\bpip\s+install\b",
        r"\bcargo\s+install\b",
        # Redirects
        r">\s*\S",
        r">>\s*\S",
        r"\|\s*\S",
    ]
    
    def is_allowed(self, command: str) -> tuple[bool, str]:
        """Check if a bash command is allowed.
        
        Args:
            command: The bash command to check
            
        Returns:
            Tuple of (is_allowed, reason_if_blocked)
        """
        import re
        
        command = command.strip()
        
        # Check blocked patterns first
        for pattern in self.BLOCKED_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return False, f"Command matches blocked pattern: {pattern}"
        
        # Extract the base command
        base_cmd = command.split()[0] if command.split() else ""
        
        # Check if base command is in allowed list
        for allowed in self.READ_ONLY_COMMANDS:
            if command.startswith(allowed) or base_cmd == allowed.split()[0]:
                return True, ""
        
        # Check for git subcommands
        if command.startswith("git "):
            parts = command.split()
            if len(parts) >= 2:
                subcmd = f"git {parts[1]}"
                if subcmd in self.READ_ONLY_COMMANDS:
                    return True, ""
        
        # Unknown command - be conservative
        return False, f"Command not in read-only allowlist: {base_cmd}"


class SubagentRunner:
    """Runs subagents with restricted tool access."""
    
    def __init__(
        self,
        provider: LLMProvider,
        session_manager: SessionManager,
        model: str,
        tool_registry: ToolRegistry,
    ):
        """Initialize subagent runner.
        
        Args:
            provider: LLM provider for the subagent
            session_manager: Session manager for creating sessions
            model: Model name to use
            tool_registry: Tool registry to source tools from
        """
        self._provider = provider
        self._session_manager = session_manager
        self._model = model
        self._tool_registry = tool_registry
        self._bash_filter = ReadOnlyBashFilter()
    
    def _create_filtered_registry(self, config: SubagentConfig) -> ToolRegistry:
        """Create a filtered tool registry with only allowed tools.
        
        Args:
            config: Subagent configuration
            
        Returns:
            New ToolRegistry with only whitelisted tools
        """
        from codepi.tools.base import ToolRegistry
        
        filtered = ToolRegistry()
        
        for tool_name in config.tools:
            tool = self._tool_registry.get(tool_name)
            if tool:
                # Wrap bash tool if read_only mode
                if tool_name == "bash" and config.read_only:
                    tool = self._wrap_bash_readonly(tool)
                filtered.register(tool)
        
        return filtered
    
    def _wrap_bash_readonly(self, tool):
        """Wrap bash tool to enforce read-only mode."""
        from codepi.tools.base import Tool, ToolResult
        from functools import wraps
        
        original_execute = tool.execute
        
        @wraps(original_execute)
        async def readonly_execute(**kwargs):
            command = kwargs.get("command", "")
            is_allowed, reason = self._bash_filter.is_allowed(command)
            
            if not is_allowed:
                return ToolResult(
                    error=f"Read-only mode: {reason}. "
                          f"Only read-only operations are allowed."
                )
            
            return await original_execute(**kwargs)
        
        # Create wrapped tool
        tool.execute = readonly_execute
        return tool
    
    async def run(
        self,
        config: SubagentConfig,
        prompt: str,
    ) -> SubagentResult:
        """Run a subagent with the given configuration.
        
        Args:
            config: Subagent configuration
            prompt: User prompt for the subagent
            
        Returns:
            SubagentResult with output and status
        """
        from codepi.ai.provider import TokenEvent, LLMToolCallEvent, DoneEvent
        
        result = SubagentResult(status=SubagentStatus.RUNNING)
        filtered_registry = self._create_filtered_registry(config)
        
        messages = [{"role": "user", "content": prompt}]
        assistant_content: list[str] = []
        turn_count = 0
        
        try:
            while turn_count < config.max_turns:
                tool_calls_this_round: list[dict] = []
                tool_results: list[dict] = []
                pending_assistant_msg: dict | None = None
                
                async for event in self._provider.stream(
                    messages=messages,
                    tools=filtered_registry.to_openai_schema(),
                    model=self._model,
                    system=config.system_prompt,
                ):
                    if isinstance(event, TokenEvent):
                        assistant_content.append(event.text)
                    
                    elif isinstance(event, LLMToolCallEvent):
                        # Track tool call
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
                        
                        result.tool_calls.append({
                            "name": event.name,
                            "arguments": event.arguments,
                        })
                        
                        # Execute tool
                        import json
                        tool = filtered_registry.get(event.name)
                        if tool:
                            tool_result = await tool.execute(**(event.arguments or {}))
                        else:
                            tool_result = ToolResult(error=f"Unknown tool: {event.name}")
                        
                        tool_results.append({
                            "role": "tool",
                            "tool_call_id": event.id,
                            "content": tool_result.to_message_content(),
                        })
                    
                    elif isinstance(event, DoneEvent):
                        result.tokens_used += event.usage.input_tokens
                
                # If we had tool calls, continue the loop
                if pending_assistant_msg and tool_results:
                    pending_assistant_msg["content"] = "".join(assistant_content)
                    messages.append(pending_assistant_msg)
                    messages.extend(tool_results)
                    assistant_content = []
                    turn_count += 1
                    continue
                
                # No tool calls - we're done
                break
            
            result.output = "".join(assistant_content)
            result.status = SubagentStatus.COMPLETED
            
        except asyncio.TimeoutError:
            result.status = SubagentStatus.FAILED
            result.error = f"Subagent timed out after {config.timeout_seconds}s"
        except Exception as e:
            result.status = SubagentStatus.FAILED
            result.error = str(e)
            logger.error(f"Subagent {config.name} failed: {e}")
        
        return result
    
    async def run_concurrent(
        self,
        configs_and_prompts: list[tuple[SubagentConfig, str]],
    ) -> list[SubagentResult]:
        """Run multiple subagents concurrently.
        
        Args:
            configs_and_prompts: List of (config, prompt) tuples
            
        Returns:
            List of SubagentResults in same order as input
        """
        tasks = [
            self.run(config, prompt)
            for config, prompt in configs_and_prompts
        ]
        return await asyncio.gather(*tasks)
