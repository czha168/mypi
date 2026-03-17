from __future__ import annotations
from abc import ABC
from dataclasses import dataclass, field
from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from mypi.core.events import (
        BeforeAgentStartEvent, BeforeProviderRequestEvent,
        ToolCallEvent, ToolResultEvent, SessionForkEvent, SessionTreeEvent
    )
    from mypi.tools.base import Tool


@dataclass
class UIComponents:
    header: Callable[[], str] | None = None
    footer: Callable[[], str] | None = None
    widgets: dict[str, Callable[[], str]] = field(default_factory=dict)


class Extension(ABC):
    name: str

    # Mutable hooks — return modified event or None (no-op, keep original)
    async def on_before_agent_start(self, event: "BeforeAgentStartEvent") -> "BeforeAgentStartEvent | None":
        return None

    async def on_before_provider_request(self, event: "BeforeProviderRequestEvent") -> "BeforeProviderRequestEvent | None":
        return None

    async def on_tool_call(self, event: "ToolCallEvent") -> "ToolCallEvent | None":
        return None

    async def on_tool_result(self, event: "ToolResultEvent") -> "ToolResultEvent | None":
        return None

    # Notification hooks — observation only
    async def on_session_fork(self, event: "SessionForkEvent") -> None:
        pass

    async def on_session_tree(self, event: "SessionTreeEvent") -> None:
        pass

    # Registration
    def get_tools(self) -> list["Tool"]:
        return []

    def get_shortcuts(self) -> dict[str, Callable]:
        return {}

    def get_ui_components(self) -> UIComponents | None:
        return None
