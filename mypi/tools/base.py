from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable
from mypi.core.events import ToolCallEvent, ToolResultEvent


@dataclass
class ToolResult:
    output: str = ""
    error: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)

    def to_message_content(self) -> str:
        if self.error:
            return f"Error: {self.error}"
        return self.output


class Tool(ABC):
    name: str
    description: str
    input_schema: dict

    async def execute(self, *args, **kwargs) -> ToolResult:
        raise NotImplementedError

    def to_openai_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema,
            },
        }


@runtime_checkable
class ExtensionRunner(Protocol):
    """Chains extension hooks for tool interception."""
    async def fire_tool_call(self, event: ToolCallEvent) -> ToolCallEvent: ...
    async def fire_tool_result(self, event: ToolResultEvent) -> ToolResultEvent: ...


class _WrappedTool(Tool):
    """Tool wrapped with extension interception."""

    def __init__(self, inner: Tool, runner: ExtensionRunner):
        self.name = inner.name
        self.description = inner.description
        self.input_schema = inner.input_schema
        self._inner = inner
        self._runner = runner

    async def execute(self, **kwargs) -> ToolResult:
        call_event = ToolCallEvent(tool_name=self.name, arguments=kwargs)
        call_event = await self._runner.fire_tool_call(call_event)
        result = await self._inner.execute(**call_event.arguments)
        result_event = ToolResultEvent(tool_name=self.name, result=result)
        result_event = await self._runner.fire_tool_result(result_event)
        return result_event.result


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def wrap(self, tool: Tool, runner: ExtensionRunner) -> Tool:
        """Wrap a registered tool with extension interception.

        Replaces the tool in the registry with a wrapped version.
        Calling wrap() twice on the same tool name overwrites the first wrapper.
        """
        wrapped = _WrappedTool(tool, runner)
        self._tools[tool.name] = wrapped
        return wrapped

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def to_openai_schema(self) -> list[dict]:
        return [t.to_openai_schema() for t in self._tools.values()]

    def all_tools(self) -> list[Tool]:
        return list(self._tools.values())
