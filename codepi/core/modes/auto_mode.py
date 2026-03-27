"""Auto mode implementation for continuous autonomous execution.

Auto mode enables the agent to execute continuously with minimal user interruption,
making reasonable assumptions and proceeding with implementation directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from codepi.core.security import SecurityDecision


class AutoModeState(Enum):
    """Auto mode states."""
    DISABLED = "disabled"
    ACTIVE = "active"
    PAUSED = "paused"  # Paused for user input
    LIMIT_REACHED = "limit_reached"


@dataclass
class AutoModeConfig:
    """Configuration for auto mode behavior."""
    enabled: bool = False
    max_iterations: int = 100
    require_approval_for: list[str] = field(default_factory=lambda: ["push", "pr", "publish"])
    pause_on_errors: bool = True
    auto_run_tests: bool = True
    auto_run_lint: bool = True

    def __post_init__(self):
        """Validate configuration."""
        if self.max_iterations < 1:
            self.max_iterations = 100
        if not self.require_approval_for:
            self.require_approval_for = ["push", "pr", "publish"]


@dataclass
class AutoModeContext:
    """Runtime context for auto mode."""
    iteration_count: int = 0
    tools_used: list[str] = field(default_factory=list)
    files_modified: list[str] = field(default_factory=list)
    errors_encountered: int = 0
    approvals_requested: int = 0
    state: AutoModeState = AutoModeState.DISABLED

    def increment_iteration(self, max_iterations: int = 100) -> bool:
        """Increment iteration count and check if limit reached.

        Args:
            max_iterations: Maximum allowed iterations

        Returns:
            True if under limit, False if limit reached
        """
        self.iteration_count += 1
        return self.iteration_count < max_iterations

    def record_tool_use(self, tool_name: str) -> None:
        """Record a tool usage."""
        self.tools_used.append(tool_name)

    def record_file_modification(self, file_path: str) -> None:
        """Record a file modification."""
        if file_path not in self.files_modified:
            self.files_modified.append(file_path)

    def record_error(self) -> None:
        """Record an error occurrence."""
        self.errors_encountered += 1

    def to_dict(self) -> dict[str, Any]:
        """Serialize context to dictionary."""
        return {
            "iteration_count": self.iteration_count,
            "tools_used": self.tools_used,
            "files_modified": self.files_modified,
            "errors_encountered": self.errors_encountered,
            "approvals_requested": self.approvals_requested,
            "state": self.state.value,
        }


class AutoModeManager:
    """Manages auto mode behavior for an agent session."""

    # Operations that always require approval, even in auto mode
    SENSITIVE_OPERATIONS = {
        "push": ["git push", "git push origin"],
        "pr": ["gh pr create", "gh pr merge"],
        "publish": ["npm publish", "pip upload", "cargo publish", "twine upload"],
        "deploy": ["kubectl apply", "terraform apply", "ansible-playbook"],
    }

    def __init__(
        self,
        config: AutoModeConfig | None = None,
        on_iteration_limit: Callable[[int], bool] | None = None,
        on_approval_needed: Callable[[str, str], bool] | None = None,
    ):
        """Initialize auto mode manager.

        Args:
            config: Auto mode configuration
            on_iteration_limit: Callback when iteration limit reached, returns True to continue
            on_approval_needed: Callback when approval needed for operation, returns True if approved
        """
        self.config = config or AutoModeConfig()
        self.context = AutoModeContext(state=AutoModeState.ACTIVE if self.config.enabled else AutoModeState.DISABLED)
        self._on_iteration_limit = on_iteration_limit
        self._on_approval_needed = on_approval_needed

    @property
    def is_active(self) -> bool:
        """Check if auto mode is currently active."""
        return self.context.state == AutoModeState.ACTIVE

    @property
    def is_paused(self) -> bool:
        """Check if auto mode is paused."""
        return self.context.state == AutoModeState.PAUSED

    def start(self) -> None:
        """Start auto mode."""
        self.config.enabled = True
        self.context.state = AutoModeState.ACTIVE
        self.context.iteration_count = 0

    def stop(self) -> AutoModeContext:
        """Stop auto mode and return final context.

        Returns:
            The final auto mode context
        """
        final_context = AutoModeContext(
            iteration_count=self.context.iteration_count,
            tools_used=list(self.context.tools_used),
            files_modified=list(self.context.files_modified),
            errors_encountered=self.context.errors_encountered,
            approvals_requested=self.context.approvals_requested,
            state=AutoModeState.DISABLED,
        )
        self.config.enabled = False
        self.context.state = AutoModeState.DISABLED
        return final_context

    def pause(self, reason: str = "") -> None:
        """Pause auto mode.

        Args:
            reason: Reason for pausing
        """
        self.context.state = AutoModeState.PAUSED

    def resume(self) -> None:
        """Resume auto mode from pause."""
        if self.context.state == AutoModeState.PAUSED:
            self.context.state = AutoModeState.ACTIVE

    def check_iteration_limit(self) -> tuple[bool, str]:
        """Check if iteration limit has been reached.

        Returns:
            Tuple of (can_continue, message)
        """
        if not self.is_active:
            return True, "Auto mode not active"

        self.context.iteration_count += 1

        if self.context.iteration_count >= self.config.max_iterations:
            self.context.state = AutoModeState.LIMIT_REACHED

            if self._on_iteration_limit:
                should_continue = self._on_iteration_limit(self.context.iteration_count)
                if should_continue:
                    self.context.state = AutoModeState.ACTIVE
                    return True, f"Iteration limit extended (now at {self.context.iteration_count})"

            return False, f"Iteration limit reached ({self.config.max_iterations})"

        return True, f"Iteration {self.context.iteration_count}/{self.config.max_iterations}"

    def requires_approval(self, operation: str, tool_name: str, arguments: dict) -> bool:
        """Check if an operation requires user approval in auto mode.

        Args:
            operation: Operation type (push, pr, publish, etc.)
            tool_name: Tool being called
            arguments: Tool arguments

        Returns:
            True if approval is required
        """
        if not self.is_active:
            return False

        # Check if operation is in require_approval_for list
        if operation in self.config.require_approval_for:
            return True

        # Check bash commands for sensitive patterns
        if tool_name == "bash":
            command = arguments.get("command", "").lower()
            for op_type, patterns in self.SENSITIVE_OPERATIONS.items():
                if op_type in self.config.require_approval_for:
                    for pattern in patterns:
                        if pattern.lower() in command:
                            return True

        return False

    def check_and_request_approval(
        self,
        operation: str,
        tool_name: str,
        arguments: dict,
        security_decision: "SecurityDecision | None" = None,
    ) -> tuple[bool, str]:
        """Check if approval is needed and request it.

        Args:
            operation: Operation type
            tool_name: Tool being called
            arguments: Tool arguments
            security_decision: Optional security decision from security monitor

        Returns:
            Tuple of (approved, message)
        """
        if not self.is_active:
            return True, "Auto mode not active, approval not required"

        # Check security decision first
        if security_decision:
            from codepi.core.security import SecurityAction
            if security_decision.action == SecurityAction.BLOCK:
                return False, f"Blocked by security: {security_decision.reason}"
            if security_decision.action == SecurityAction.ASK:
                if self._on_approval_needed:
                    self.context.approvals_requested += 1
                    approved = self._on_approval_needed(security_decision.reason, security_decision.rule_id)
                    return approved, "Approved by user" if approved else "Rejected by user"
                return False, f"Requires approval: {security_decision.reason}"

        # Check our own approval logic
        if self.requires_approval(operation, tool_name, arguments):
            if self._on_approval_needed:
                self.context.approvals_requested += 1
                reason = f"Sensitive operation: {operation}"
                approved = self._on_approval_needed(reason, operation)
                return approved, "Approved by user" if approved else "Rejected by user"
            return False, f"Requires approval: {operation}"

        return True, "Approved"

    def get_prompt_context(self) -> dict[str, Any]:
        """Get context for auto mode prompting.

        Returns:
            Dictionary with auto mode context for prompt templates
        """
        return {
            "auto_mode_active": self.is_active,
            "iteration_count": self.context.iteration_count,
            "max_iterations": self.config.max_iterations,
            "require_approval_for": self.config.require_approval_for,
            "files_modified": self.context.files_modified,
            "errors_encountered": self.context.errors_encountered,
        }

    def get_auto_mode_directive(self) -> str:
        """Get the auto mode directive for system prompt.

        Returns:
            Directive string for auto mode
        """
        if not self.is_active:
            return ""

        approval_list = ", ".join(self.config.require_approval_for)

        return f"""## Auto Mode Active

Auto mode is enabled for continuous, autonomous execution.

**Behavior Guidelines:**
1. **Execute immediately** — Start implementing right away
2. **Minimize interruptions** — Make reasonable assumptions instead of asking
3. **Prefer action over planning** — Do not enter plan mode unless explicitly asked
4. **Make reasonable decisions** — Choose sensible defaults when ambiguous
5. **Be thorough** — Complete the full task including tests and verification

**Limits:**
- Current iteration: {self.context.iteration_count}/{self.config.max_iterations}
- Operations requiring approval: {approval_list}

**Safety Rules:**
Even in auto mode, certain operations still require approval:
- Pushing to remote repositories
- Creating/modifying pull requests
- Publishing packages
- Posting to external services

**Never post to public services without explicit written approval.**
"""


def get_sensitive_operation_from_command(command: str) -> str | None:
    """Determine the sensitive operation type from a bash command.

    Args:
        command: Bash command string

    Returns:
        Operation type if sensitive, None otherwise
    """
    command_lower = command.lower()

    # Check git operations
    if "git push" in command_lower:
        if "--force" in command_lower or "-f " in command_lower:
            return "force_push"
        return "push"

    if "gh pr" in command_lower:
        return "pr"

    # Check publish operations
    if any(pub in command_lower for pub in ["npm publish", "twine upload", "cargo publish"]):
        return "publish"

    # Check deploy operations
    if any(dep in command_lower for dep in ["kubectl apply", "terraform apply"]):
        return "deploy"

    return None
