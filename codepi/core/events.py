from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from codepi.tools.base import ToolResult


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


# ---------------------------------------------------------------------------
# Subagent events — for subagent lifecycle
# ---------------------------------------------------------------------------

@dataclass
class SubagentStartEvent:
    """Dispatched when a subagent starts execution."""
    subagent_name: str
    config: dict  # SubagentConfig as dict
    prompt: str


@dataclass
class SubagentEndEvent:
    """Dispatched when a subagent completes execution."""
    subagent_name: str
    status: str  # SubagentStatus value
    output: str
    error: str | None = None
    tokens_used: int = 0


# ---------------------------------------------------------------------------
# Mode events — for mode switching
# ---------------------------------------------------------------------------

@dataclass
class ModeChangeEvent:
    """Dispatched when operation mode changes."""
    from_mode: str  # "normal", "plan", "auto"
    to_mode: str
    phase: int | None = None  # For plan mode: current phase (1-5)


@dataclass
class PlanModePhaseEvent:
    """Dispatched when plan mode advances to a new phase."""
    phase: int  # 1-5: UNDERSTAND, DESIGN, REVIEW, FINALIZE, EXIT
    phase_name: str
    plan_file: str | None = None
