import pytest
from mypi.tools.base import Tool, ToolResult, ToolRegistry, ExtensionRunner
from mypi.core.events import ToolCallEvent, ToolResultEvent


class EchoTool(Tool):
    name = "echo"
    description = "Echoes input"
    input_schema = {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}

    async def execute(self, text: str) -> ToolResult:
        return ToolResult(output=text)


@pytest.mark.asyncio
async def test_tool_execute():
    tool = EchoTool()
    result = await tool.execute(text="hello")
    assert result.output == "hello"
    assert result.error is None


def test_registry_registers_tool():
    reg = ToolRegistry()
    reg.register(EchoTool())
    schema = reg.to_openai_schema()
    assert any(t["function"]["name"] == "echo" for t in schema)


@pytest.mark.asyncio
async def test_registry_wrap_intercepts_call():
    reg = ToolRegistry()
    tool = EchoTool()
    reg.register(tool)

    intercepted_calls = []

    class MockRunner:
        async def fire_tool_call(self, event: ToolCallEvent) -> ToolCallEvent:
            intercepted_calls.append(event)
            return event

        async def fire_tool_result(self, event: ToolResultEvent) -> ToolResultEvent:
            return event

    wrapped = reg.wrap(tool, MockRunner())
    result = await wrapped.execute(text="test")
    assert result.output == "test"
    assert len(intercepted_calls) == 1
    assert intercepted_calls[0].tool_name == "echo"
