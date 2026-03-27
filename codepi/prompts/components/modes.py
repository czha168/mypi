"""Mode-specific prompt components for plan mode and auto mode."""

from typing import Any


PLAN_MODE_CONSTRAINTS = """
## Plan Mode Active

You are in PLAN MODE. This is a structured planning workflow that operates in phases.

### Current Behavior Restrictions

**CRITICAL**: During planning phases, you are RESTRICTED from modifying files.

- **UNDERSTAND Phase**: Read-only exploration. Use read, grep, find, ls tools only.
- **DESIGN Phase**: Continue read-only. Design the implementation approach.
- **REVIEW Phase**: Await user approval. No modifications allowed.
- **FINALIZE Phase**: You may ONLY write to the designated plan file.
- **EXIT Phase**: Planning complete. Return to normal operation.

### What You Should Do

1. **Explore thoroughly** in UNDERSTAND phase
2. **Design carefully** in DESIGN phase with clear implementation steps
3. **Wait for approval** in REVIEW phase before proceeding
4. **Document the plan** in FINALIZE phase
5. **Implement after exit** - edits are blocked until plan mode exits

If the user asks to make changes before approval, remind them you're in plan mode.
"""

AUTO_MODE_CONSTRAINTS = """
## Auto Mode Active

Auto mode is enabled for continuous, autonomous execution.

### Behavior Guidelines

1. **Execute immediately** — Start implementing right away
2. **Minimize interruptions** — Make reasonable assumptions instead of asking
3. **Prefer action over planning** — Do not enter plan mode unless explicitly asked
4. **Make reasonable decisions** — Choose sensible defaults when ambiguous
5. **Be thorough** — Complete the full task including tests and verification

### Limits

- Maximum iterations: {{max_iterations}}
- Operations requiring approval: {{require_approval_for}}

### Safety Rules

Even in auto mode, certain operations still require approval:
- Pushing to remote repositories
- Creating/modifying pull requests
- Publishing packages
- Posting to external services

**Never post to public services without explicit written approval.**
"""

PLAN_MODE_PHASE_PROMPTS = {
    "understand": """## Plan Mode Phase 1: UNDERSTAND

Your goal is to explore the codebase and gather context for planning.

**Tasks:**
1. Use read, grep, find, ls to explore relevant code
2. Identify key files, patterns, and existing implementations
3. Note any constraints or dependencies
4. Ask clarifying questions if requirements are ambiguous

**Constraints:**
- DO NOT edit any files in this phase
- Focus on understanding, not implementing
- Signal when ready to advance to DESIGN

**Output:** Summary of findings and any clarifying questions.
""",
    "design": """## Plan Mode Phase 2: DESIGN

Your goal is to create a detailed implementation plan.

**Tasks:**
1. Based on exploration, design the implementation approach
2. Break down work into clear, actionable steps
3. Identify files to modify and create
4. Consider edge cases and potential issues
5. Define testing approach

**Plan Format:**
```
## Goal
[Clear statement of what we're building]

## Approach
[High-level strategy]

## Files to Modify
- file1.py: [what changes]
- file2.py: [what changes]

## Implementation Steps
1. [First step with details]
2. [Second step with details]
...

## Testing
[How to verify the changes work]

## Risks
[Potential issues and mitigations]
```

**Constraints:**
- DO NOT edit any files in this phase
- Design only, implementation comes later

**Output:** Complete implementation plan.
""",
    "review": """## Plan Mode Phase 3: REVIEW

The plan has been created and is awaiting your review.

**What happens next:**
- If you approve: Type "approve" or "looks good" to proceed
- If you want changes: Describe what needs to be revised

The agent will wait for your feedback before proceeding.
""",
    "finalize": """## Plan Mode Phase 4: FINALIZE

Your goal is to write the approved plan to a file.

**Tasks:**
1. Write the complete plan to the designated plan file
2. Ensure all sections are well-documented
3. Include any relevant context for future reference

**This is the ONLY phase where file writes are allowed in plan mode.**

After writing, plan mode will exit and normal implementation can begin.
""",
    "exit": """## Plan Mode Phase 5: EXIT

Plan mode is complete. You are now returning to normal operation.

**What happens next:**
- File edits are now allowed
- You can begin implementing the plan
- Tool usage is no longer restricted

Proceed with implementation based on the approved plan.
""",
}


def get_plan_mode_prompt(
    phase: str | int | None = None,
    include_constraints: bool = True,
) -> str:
    """Get the plan mode prompt for the current phase.

    Args:
        phase: Phase name (str) or number (int). If None, returns base constraints.
        include_constraints: Whether to include base constraints

    Returns:
        Combined prompt string for plan mode
    """
    parts = []

    if include_constraints:
        parts.append(PLAN_MODE_CONSTRAINTS.strip())

    if phase is not None:
        phase_key = None
        if isinstance(phase, int):
            phase_map = {1: "understand", 2: "design", 3: "review", 4: "finalize", 5: "exit"}
            phase_key = phase_map.get(phase)
        elif isinstance(phase, str):
            phase_key = phase.lower()

        if phase_key and phase_key in PLAN_MODE_PHASE_PROMPTS:
            parts.append(PLAN_MODE_PHASE_PROMPTS[phase_key].strip())

    return "\n\n".join(parts)


def get_auto_mode_prompt(
    max_iterations: int = 100,
    require_approval_for: list[str] | None = None,
    include_constraints: bool = True,
) -> str:
    """Get the auto mode prompt with configured values.

    Args:
        max_iterations: Maximum iterations before pause
        require_approval_for: List of operations requiring approval
        include_constraints: Whether to include constraints

    Returns:
        Configured auto mode prompt string
    """
    if not include_constraints:
        return ""

    approval_list = require_approval_for or ["push", "pr", "publish"]
    approval_str = ", ".join(approval_list)

    return AUTO_MODE_CONSTRAINTS.replace(
        "{{max_iterations}}", str(max_iterations)
    ).replace(
        "{{require_approval_for}}", approval_str
    )


def format_mode_context(
    mode: str,
    phase: str | int | None = None,
    **kwargs: Any,
) -> str:
    """Format mode-specific context for prompts.

    Args:
        mode: Current mode ("normal", "plan", "auto")
        phase: Current phase (for plan mode)
        **kwargs: Additional context values

    Returns:
        Formatted context string for prompts
    """
    if mode == "plan":
        return get_plan_mode_prompt(phase=phase, **kwargs)
    elif mode == "auto":
        return get_auto_mode_prompt(**kwargs)
    else:
        return ""


# Export mode-related constants
MODE_INDICATORS = {
    "normal": "",
    "plan": "[PLAN MODE]",
    "auto": "[AUTO MODE]",
}

MODE_DESCRIPTIONS = {
    "normal": "Normal interactive mode",
    "plan": "Structured planning workflow",
    "auto": "Continuous autonomous execution",
}
