"""Plan mode implementation for structured planning workflow.

Plan mode follows a 5-phase workflow:
1. UNDERSTAND → Explore codebase, ask clarifying questions
2. DESIGN → Create implementation plan
3. REVIEW → User reviews and approves
4. FINALIZE → Write plan to file
5. EXIT → Return to normal mode
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from codepi.core.agent_session import AgentSession
    from codepi.core.subagent import SubagentRunner


class PlanPhase(Enum):
    """Plan mode phases."""
    UNDERSTAND = 1
    DESIGN = 2
    REVIEW = 3
    FINALIZE = 4
    EXIT = 5

    @classmethod
    def from_int(cls, value: int) -> "PlanPhase":
        """Convert integer to PlanPhase."""
        try:
            return cls(value)
        except ValueError:
            return cls.UNDERSTAND

    def next(self) -> "PlanPhase":
        """Get the next phase."""
        if self == PlanPhase.EXIT:
            return PlanPhase.EXIT
        return PlanPhase(self.value + 1)

    def prev(self) -> "PlanPhase":
        """Get the previous phase."""
        if self == PlanPhase.UNDERSTAND:
            return PlanPhase.UNDERSTAND
        return PlanPhase(self.value - 1)


PHASE_NAMES = {
    PlanPhase.UNDERSTAND: "UNDERSTAND",
    PlanPhase.DESIGN: "DESIGN",
    PlanPhase.REVIEW: "REVIEW",
    PlanPhase.FINALIZE: "FINALIZE",
    PlanPhase.EXIT: "EXIT",
}

PHASE_DESCRIPTIONS = {
    PlanPhase.UNDERSTAND: "Exploring codebase and gathering context",
    PlanPhase.DESIGN: "Creating implementation plan",
    PlanPhase.REVIEW: "Awaiting user review and approval",
    PlanPhase.FINALIZE: "Writing plan to file",
    PlanPhase.EXIT: "Exiting plan mode",
}


@dataclass
class PlanModeState:
    """State for plan mode workflow."""
    phase: PlanPhase = PlanPhase.UNDERSTAND
    plan_file: Path | None = None
    exploration_results: list[str] = field(default_factory=list)
    design_content: str | None = None
    user_request: str | None = None
    iteration_count: int = 0
    started_at: datetime = field(default_factory=datetime.now)

    def is_edit_allowed(self, file_path: str | Path | None = None) -> bool:
        """Check if editing is allowed in current phase.

        In plan mode, edits are only allowed:
        - In FINALIZE phase (writing the plan file)
        - When editing the designated plan file

        Args:
            file_path: Path to the file being edited

        Returns:
            True if edit is allowed, False otherwise
        """
        # In FINALIZE phase, we can write the plan file
        if self.phase == PlanPhase.FINALIZE:
            if file_path and self.plan_file:
                return Path(file_path) == self.plan_file
            return True  # Allow if we're finalizing (plan file might not be set yet)

        # All other phases block edits
        return False

    def can_advance(self) -> tuple[bool, str]:
        """Check if we can advance to the next phase.

        Returns:
            Tuple of (can_advance, reason_if_not)
        """
        if self.phase == PlanPhase.UNDERSTAND:
            if not self.exploration_results:
                return False, "Exploration not complete"
            return True, ""

        if self.phase == PlanPhase.DESIGN:
            if not self.design_content:
                return False, "Design not complete"
            return True, ""

        if self.phase == PlanPhase.REVIEW:
            # REVIEW requires explicit user approval
            return False, "Awaiting user approval"

        if self.phase == PlanPhase.FINALIZE:
            return True, ""

        if self.phase == PlanPhase.EXIT:
            return False, "Already in EXIT phase"

        return True, ""

    def advance(self) -> bool:
        """Advance to the next phase if possible.

        Returns:
            True if advanced, False if blocked
        """
        can_advance, _ = self.can_advance()
        if can_advance:
            self.phase = self.phase.next()
            return True
        return False

    def reject_and_return(self) -> None:
        """User rejected the plan, return to DESIGN phase."""
        self.phase = PlanPhase.DESIGN
        self.iteration_count += 1

    def get_plan_filename(self, base_dir: Path | None = None) -> Path:
        """Get the plan file path.

        Args:
            base_dir: Optional base directory for the plan file

        Returns:
            Path to the plan file
        """
        if self.plan_file:
            return self.plan_file

        # Generate default plan file path
        if base_dir is None:
            base_dir = Path.cwd()

        timestamp = self.started_at.strftime("%Y%m%d-%H%M%S")
        return base_dir / ".codepi" / "plans" / f"plan-{timestamp}.md"

    def to_dict(self) -> dict[str, Any]:
        """Serialize state to dictionary for persistence."""
        return {
            "phase": self.phase.value,
            "plan_file": str(self.plan_file) if self.plan_file else None,
            "exploration_results": self.exploration_results,
            "design_content": self.design_content,
            "user_request": self.user_request,
            "iteration_count": self.iteration_count,
            "started_at": self.started_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PlanModeState":
        """Deserialize state from dictionary."""
        return cls(
            phase=PlanPhase.from_int(data.get("phase", 1)),
            plan_file=Path(data["plan_file"]) if data.get("plan_file") else None,
            exploration_results=data.get("exploration_results", []),
            design_content=data.get("design_content"),
            user_request=data.get("user_request"),
            iteration_count=data.get("iteration_count", 0),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else datetime.now(),
        )


@dataclass
class PlanModeConfig:
    """Configuration for plan mode behavior."""
    enabled: bool = False
    auto_advance: bool = False  # Automatically advance phases
    require_explicit_approval: bool = True  # Require user approval before EXIT
    max_iterations: int = 5  # Max design iterations before forcing exit
    default_plan_dir: Path = field(default_factory=lambda: Path.cwd() / ".codepi" / "plans")

    def __post_init__(self):
        if isinstance(self.default_plan_dir, str):
            self.default_plan_dir = Path(self.default_plan_dir)


class PlanModeManager:
    """Manages plan mode workflow for an agent session."""

    def __init__(
        self,
        config: PlanModeConfig | None = None,
        on_phase_change: Callable[[PlanPhase, PlanPhase], None] | None = None,
        on_approval_required: Callable[[str], bool] | None = None,
    ):
        """Initialize plan mode manager.

        Args:
            config: Plan mode configuration
            on_phase_change: Callback when phase changes (old_phase, new_phase)
            on_approval_required: Callback when user approval is needed, returns True if approved
        """
        self.config = config or PlanModeConfig()
        self.state = PlanModeState() if self.config.enabled else None
        self._on_phase_change = on_phase_change
        self._on_approval_required = on_approval_required

    @property
    def is_active(self) -> bool:
        """Check if plan mode is currently active."""
        return self.state is not None and self.state.phase != PlanPhase.EXIT

    def start(self, user_request: str, plan_file: Path | None = None) -> None:
        """Start plan mode with a user request.

        Args:
            user_request: The initial user request to plan for
            plan_file: Optional specific path for the plan file
        """
        self.state = PlanModeState(
            phase=PlanPhase.UNDERSTAND,
            user_request=user_request,
            plan_file=plan_file,
        )

    def stop(self) -> PlanModeState | None:
        """Stop plan mode and return the final state.

        Returns:
            The final plan mode state, or None if not active
        """
        final_state = self.state
        self.state = None
        return final_state

    def add_exploration_result(self, result: str) -> None:
        """Add an exploration result in UNDERSTAND phase.

        Args:
            result: Description of exploration findings
        """
        if self.state:
            self.state.exploration_results.append(result)

    def set_design_content(self, content: str) -> None:
        """Set the design content in DESIGN phase.

        Args:
            content: The plan/design content
        """
        if self.state:
            self.state.design_content = content

    def try_advance(self) -> tuple[bool, str]:
        """Try to advance to the next phase.

        Returns:
            Tuple of (success, message)
        """
        if not self.state:
            return False, "Plan mode not active"

        old_phase = self.state.phase

        # Special handling for REVIEW phase
        if self.state.phase == PlanPhase.REVIEW:
            if self._on_approval_required:
                design = self.state.design_content or "No design available"
                approved = self._on_approval_required(design)
                if not approved:
                    self.state.reject_and_return()
                    if self._on_phase_change:
                        self._on_phase_change(PlanPhase.REVIEW, PlanPhase.DESIGN)
                    return False, "Plan rejected, returning to DESIGN phase"

        can_advance, reason = self.state.can_advance()
        if not can_advance:
            return False, reason

        self.state.advance()

        if self._on_phase_change:
            self._on_phase_change(old_phase, self.state.phase)

        return True, f"Advanced to {PHASE_NAMES[self.state.phase]}"

    def get_phase_prompt_context(self) -> dict[str, Any]:
        """Get context for phase-specific prompting.

        Returns:
            Dictionary with phase context for prompt templates
        """
        if not self.state:
            return {"plan_mode_active": False}

        return {
            "plan_mode_active": True,
            "phase": self.state.phase.value,
            "phase_name": PHASE_NAMES.get(self.state.phase, "UNKNOWN"),
            "phase_description": PHASE_DESCRIPTIONS.get(self.state.phase, ""),
            "exploration_results": self.state.exploration_results,
            "design_content": self.state.design_content,
            "user_request": self.state.user_request,
            "iteration_count": self.state.iteration_count,
            "plan_file": str(self.state.plan_file) if self.state.plan_file else None,
        }

    def get_phase_directive(self) -> str:
        """Get the current phase directive for system prompt.

        Returns:
            Directive string for the current phase
        """
        if not self.state:
            return ""

        directives = {
            PlanPhase.UNDERSTAND: """## Plan Mode: UNDERSTAND Phase

You are in UNDERSTAND phase. Your goal is to explore the codebase and gather context.

**Your tasks:**
1. Use the explore subagent (or read, grep, find tools) to understand the codebase
2. Identify relevant files, patterns, and existing implementations
3. Ask clarifying questions if requirements are ambiguous
4. **DO NOT make any edits** — this phase is read-only

When you have sufficient context, signal readiness to advance to DESIGN phase.
""",
            PlanPhase.DESIGN: """## Plan Mode: DESIGN Phase

You are in DESIGN phase. Your goal is to create a detailed implementation plan.

**Your tasks:**
1. Based on your exploration, design the implementation approach
2. Break down the work into clear, actionable steps
3. Consider edge cases and potential issues
4. **DO NOT make any edits** — continue in read-only mode

Format your plan with:
- Goal statement
- Files to modify
- Step-by-step implementation
- Testing approach

When your design is complete, it will be presented for REVIEW.
""",
            PlanPhase.REVIEW: """## Plan Mode: REVIEW Phase

You are in REVIEW phase. The plan has been created and is awaiting user approval.

**Your tasks:**
1. Wait for user feedback
2. If approved, you will advance to FINALIZE
3. If rejected, you will return to DESIGN for revisions

**DO NOT make any edits** until approved.
""",
            PlanPhase.FINALIZE: """## Plan Mode: FINALIZE Phase

You are in FINALIZE phase. Write the approved plan to the designated file.

**Your tasks:**
1. Write the complete plan to the plan file
2. Ensure all sections are documented
3. This is the ONLY phase where you may write files in plan mode

After writing, you will EXIT plan mode and return to normal operation.
""",
            PlanPhase.EXIT: """## Plan Mode: EXIT Phase

You have completed the planning workflow. You are now exiting plan mode.

**What happens next:**
- You will return to normal mode
- You can now begin implementing the plan
- Edits and tool usage are no longer restricted
""",
        }

        return directives.get(self.state.phase, "")
