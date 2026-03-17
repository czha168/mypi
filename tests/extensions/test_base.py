import pytest
from mypi.extensions.base import Extension, UIComponents
from mypi.core.events import (
    BeforeAgentStartEvent, ToolCallEvent, ToolResultEvent,
    SessionForkEvent, SessionTreeEvent
)
from mypi.tools.base import ToolResult


class NullExtension(Extension):
    name = "null"


@pytest.mark.asyncio
async def test_extension_default_hooks_are_noop():
    ext = NullExtension()
    evt = BeforeAgentStartEvent(system_prompt="x", messages=[])
    result = await ext.on_before_agent_start(evt)
    assert result is None  # default noop


@pytest.mark.asyncio
async def test_extension_can_modify_system_prompt():
    class InjectExtension(Extension):
        name = "inject"
        async def on_before_agent_start(self, event: BeforeAgentStartEvent):
            return BeforeAgentStartEvent(
                system_prompt=event.system_prompt + "\ninjected",
                messages=event.messages
            )

    ext = InjectExtension()
    evt = BeforeAgentStartEvent(system_prompt="base", messages=[])
    result = await ext.on_before_agent_start(evt)
    assert result is not None
    assert "injected" in result.system_prompt


def test_ui_components_defaults():
    ui = UIComponents()
    assert ui.header is None
    assert ui.footer is None
    assert ui.widgets == {}


def test_extension_returns_no_tools_by_default():
    ext = NullExtension()
    assert ext.get_tools() == []
