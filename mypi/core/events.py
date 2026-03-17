from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mypi.tools.base import ToolResult


# ---------------------------------------------------------------------------
# Mutable events — extensions return EventType | None (None = no-op)
# ---------------------------------------------------------------------------

@dataclass
class BeforeAgentStartEvent:
    system_prompt: str
    messages: list[dict]


@dataclass
class BeforeProviderRequestEvent:
    params: dict


@dataclass
class ToolCallEvent:
    tool_name: str
    arguments: dict


@dataclass
class ToolResultEvent:
    tool_name: str
    result: "ToolResult"


# ---------------------------------------------------------------------------
# Notification events — extensions return None (observation only)
# ---------------------------------------------------------------------------

@dataclass
class SessionForkEvent:
    from_entry_id: str
    new_entry_id: str


@dataclass
class SessionTreeEvent:
    leaf_id: str


@dataclass
class TokenStreamEvent:
    """Internal rendering use only — not dispatched to extensions."""
    text: str


@dataclass
class AutoCompactionStartEvent:
    pass


@dataclass
class AutoCompactionEndEvent:
    summary: str


@dataclass
class AutoRetryStartEvent:
    attempt: int


@dataclass
class AutoRetryEndEvent:
    attempt: int
