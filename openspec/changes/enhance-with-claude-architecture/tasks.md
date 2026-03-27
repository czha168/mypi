## 1. Foundation: Modular Prompts

- [x] 1.1 Create `codepi/prompts/__init__.py` with `PromptComposer` class
- [x] 1.2 Create `codepi/prompts/components/persona.py` with base identity component
- [x] 1.3 Create `codepi/prompts/components/tools.py` with tool description formatting
- [x] 1.4 Create `codepi/prompts/components/constraints.py` with read-only and safety constraints
- [x] 1.5 Create `codepi/prompts/components/efficiency.py` with output efficiency guidelines
- [x] 1.6 Create `codepi/prompts/composer.py` with template rendering and variable interpolation
- [x] 1.7 Create `codepi/prompts/templates/base.yaml` default prompt template
- [x] 1.8 Add unit tests for prompt composition and template rendering

## 2. Subagent Framework

- [x] 2.1 Create `codepi/core/subagent.py` with `SubagentConfig` and `SubagentRunner` classes
- [x] 2.2 Add `SubagentStartEvent` and `SubagentEndEvent` to `codepi/core/events.py`
- [x] 2.3 Implement tool whitelisting in `SubagentRunner`
- [x] 2.4 Implement read-only bash command filtering
- [x] 2.5 Add unit tests for subagent framework

## 3. Explore Subagent

- [x] 3.1 Create `codepi/core/subagents/explore.py` with explore subagent config
- [x] 3.2 Create `codepi/prompts/templates/explore.yaml` prompt template
- [x] 3.3 Implement parallel file reading in explore subagent
- [x] 3.4 Add unit tests for explore subagent

## 4. Plan Subagent

- [x] 4.1 Create `codepi/core/subagents/plan.py` with plan subagent config
- [x] 4.2 Create `codepi/prompts/templates/plan.yaml` prompt template
- [x] 4.3 Add unit tests for plan subagent

## 5. Security Monitor

- [x] 5.1 Create `codepi/core/security.py` with `SecurityMonitor` class
- [x] 5.2 Implement destructive operation detection (rm -rf, DROP TABLE, etc.)
- [x] 5.3 Implement hard-to-reverse operation detection (force push, hard reset)
- [x] 5.4 Implement shared state operation detection (push, PR)
- [x] 5.5 Implement credential exposure detection (.env files, API keys)
- [x] 5.6 Add security config to `codepi/config.py`
- [x] 5.7 Integrate security monitor into `AgentSession` tool call flow
- [x] 5.8 Add unit tests for security monitor rules

## 6. Plan Mode

- [x] 6.1 Create `codepi/core/modes/plan_mode.py` with `PlanModeState` dataclass
- [x] 6.2 Implement 5-phase state machine (UNDERSTAND → DESIGN → REVIEW → FINALIZE → EXIT)
- [x] 6.3 Create `codepi/prompts/components/modes.py` with plan mode constraints
- [x] 6.4 Implement edit blocking during plan mode in `AgentSession`
- [x] 6.5 Implement user approval flow before exit
- [x] 6.6 Add `--plan` CLI flag to enter plan mode
- [x] 6.7 Add integration tests for plan mode workflow

## 7. Auto Mode

- [x] 7.1 Create `codepi/core/modes/auto_mode.py` with `AutoModeConfig`
- [x] 7.2 Create `codepi/prompts/templates/auto.yaml` with auto mode prompts
- [x] 7.3 Implement iteration limit enforcement
- [x] 7.4 Implement approval gates for sensitive operations
- [x] 7.5 Add `--auto` CLI flag to enable auto mode
- [x] 7.6 Add auto mode config to `config.toml` schema
- [x] 7.7 Add unit tests for auto mode behavior

## 8. Integration

- [x] 8.1 Update `AgentSession.__init__` to accept `PromptConfig` (backward compatible)
- [x] 8.2 Add extension hooks for mode changes in `codepi/extensions/base.py`
- [x] 8.3 Update TUI to display current mode and phase
- [x] 8.4 Add keyboard shortcuts for mode switching
- [x] 8.5 Update README.md with new features documentation
- [x] 8.6 Update CLAUDE.md with prompt architecture notes

## 9. Testing & Polish

- [x] 9.1 Run full test suite and fix any regressions
- [x] 9.2 Add integration tests for mode switching
- [x] 9.3 Add integration tests for security monitor + tool execution
- [x] 9.4 Performance test for prompt composition overhead
- [ ] 9.5 Manual end-to-end testing of plan mode workflow
- [ ] 9.6 Manual end-to-end testing of auto mode workflow
