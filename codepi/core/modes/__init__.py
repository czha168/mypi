"""Operation modes for codepi agent.

This package provides:
- Plan mode: Structured 5-phase planning workflow
- Auto mode: Continuous autonomous execution
"""

from codepi.core.modes.plan_mode import (
    PlanPhase,
    PlanModeState,
    PlanModeConfig,
    PlanModeManager,
    PHASE_NAMES,
    PHASE_DESCRIPTIONS,
)
from codepi.core.modes.auto_mode import (
    AutoModeState,
    AutoModeConfig,
    AutoModeContext,
    AutoModeManager,
    get_sensitive_operation_from_command,
)

__all__ = [
    # Plan mode
    "PlanPhase",
    "PlanModeState",
    "PlanModeConfig",
    "PlanModeManager",
    "PHASE_NAMES",
    "PHASE_DESCRIPTIONS",
    # Auto mode
    "AutoModeState",
    "AutoModeConfig",
    "AutoModeContext",
    "AutoModeManager",
    "get_sensitive_operation_from_command",
]
