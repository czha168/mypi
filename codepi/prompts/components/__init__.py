"""Prompt components package."""

from codepi.prompts.components.persona import PERSONA_BASE, PERSONA_MINIMAL
from codepi.prompts.components.tools import TOOL_USAGE_RULES, format_tool_descriptions
from codepi.prompts.components.constraints import (
    READ_ONLY_CONSTRAINTS,
    SAFETY_CONSTRAINTS,
    EXECUTION_CARE,
)
from codepi.prompts.components.efficiency import OUTPUT_EFFICIENCY, CONCISE_RESPONSE
from codepi.prompts.components.modes import (
    PLAN_MODE_CONSTRAINTS,
    AUTO_MODE_CONSTRAINTS,
    PLAN_MODE_PHASE_PROMPTS,
    get_plan_mode_prompt,
    get_auto_mode_prompt,
    format_mode_context,
    MODE_INDICATORS,
    MODE_DESCRIPTIONS,
)

__all__ = [
    "PERSONA_BASE",
    "PERSONA_MINIMAL",
    "TOOL_USAGE_RULES",
    "format_tool_descriptions",
    "READ_ONLY_CONSTRAINTS",
    "SAFETY_CONSTRAINTS",
    "EXECUTION_CARE",
    "OUTPUT_EFFICIENCY",
    "CONCISE_RESPONSE",
    "PLAN_MODE_CONSTRAINTS",
    "AUTO_MODE_CONSTRAINTS",
    "PLAN_MODE_PHASE_PROMPTS",
    "get_plan_mode_prompt",
    "get_auto_mode_prompt",
    "format_mode_context",
    "MODE_INDICATORS",
    "MODE_DESCRIPTIONS",
]
