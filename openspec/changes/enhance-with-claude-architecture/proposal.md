## Why

codepi currently uses a single monolithic system prompt (`"You are a helpful coding assistant..."`), limiting its ability to adapt behavior for different contexts. The Claude Code study (see `claude-prompts.md`) reveals a mature architecture with 110+ modular prompt components across 6 categories, enabling sophisticated behaviors like read-only exploration agents, security monitoring, plan mode, and auto mode.

This change introduces modular prompt architecture, subagent support (explore, plan, security), and operation modes (auto, plan) to make codepi more capable, safe, and flexible—without sacrificing its minimalist philosophy.

## What Changes

### Core Architecture
- **Modular prompt system**: Replace single string with composable components (persona, tools, constraints, modes, skills)
- **Subagent framework**: Add lightweight subagent infrastructure for spawning specialized agents
- **3 built-in subagents**: Explore (read-only search), Plan (architecture planning), Security Monitor (action evaluation)
- **Operation modes**: Plan mode (5-phase planning workflow), Auto mode (continuous autonomous execution)
- **Prompt template system**: YAML-based templates with variable interpolation

### Behavior Changes
- Explore subagent enforces strict read-only constraints
- Plan mode blocks edits until user approves plan
- Auto mode enables autonomous multi-step execution
- Security monitor evaluates risky operations before execution
- Output efficiency guidelines (be concise, direct)

### Files to Add/Modify
- `codepi/prompts/` — New module for modular prompt components
- `codepi/core/subagent.py` — Subagent runtime
- `codepi/core/subagents/` — Built-in subagent implementations
- `codepi/core/modes/` — Plan and Auto mode logic
- `codepi/core/agent_session.py` — Integrate prompt system, modes
- `codepi/core/events.py` — New events for subagent/mode lifecycle
- `codepi/extensions/base.py` — Extension hooks for mode changes

## Capabilities

### New Capabilities
- `modular-prompts`: Composable system prompt architecture with templates, personas, and context injection
- `subagent-explore`: Read-only exploration agent for codebase search and analysis
- `subagent-plan`: Architecture planning agent for implementation design
- `security-monitor`: Action evaluation system for risky operations (destructive, hard-to-reverse, shared-state)
- `plan-mode`: 5-phase planning workflow (understand → design → review → finalize → exit)
- `auto-mode`: Continuous autonomous execution with minimal user interruption

### Modified Capabilities
- None (all capabilities are new)

## Impact

### Affected Code
- `agent_session.py`: Core changes to support prompt composition and mode switching
- `events.py`: New event types for subagent lifecycle and mode changes
- `extensions/base.py`: New extension hooks

### Dependencies
- No new external dependencies (all Python stdlib + existing imports)

### Breaking Changes
- **BREAKING**: `AgentSession.__init__` signature changes — `system_prompt` becomes optional, accepts `PromptConfig` object
- Extension interface gains optional hooks (backward compatible via default implementations)

### Configuration
- New config section `[prompts]` in `config.toml` for customizing persona and constraints
- New config section `[modes]` for default mode behavior
