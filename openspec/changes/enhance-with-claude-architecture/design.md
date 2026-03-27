## Context

codepi is a minimalist Python coding assistant inspired by pi-coding-agent. Currently it uses a single system prompt string and lacks the sophisticated modular architecture found in Claude Code.

The `claude-prompts.md` study reveals Claude Code uses 110+ modular prompt components across 6 categories:
1. **Agent Prompts** — Subagent-specific prompts (explore, plan, security)
2. **System Prompts** — Core behavior directives
3. **System Reminders** — Context-aware reminders (plan mode, file changes)
4. **Tool Descriptions** — Tool schemas and usage rules
5. **Skills** — On-demand capability modules
6. **Data** — Embedded reference documentation

This design proposes adapting these concepts while preserving codepi's minimalist philosophy.

## Goals / Non-Goals

**Goals:**
- Implement modular prompt composition with template support
- Add lightweight subagent framework (explore, plan, security)
- Support plan mode and auto mode
- Enable output efficiency guidelines
- Maintain backward compatibility with existing extensions

**Non-Goals:**
- Full Claude Code parity (this is an incremental improvement, not a rewrite)
- Network/web capabilities (firecrawl, web search) — out of scope
- Claude Code's memory system — future work
- Agent orchestration (multiple agents coordinating) — future work
- Changing existing tool implementations

## Decisions

### D1: Prompt Module Structure

**Decision**: Create `codepi/prompts/` package with:
```
prompts/
├── __init__.py          # PromptComposer class
├── components/
│   ├── __init__.py
│   ├── persona.py       # Base identity
│   ├── tools.py         # Tool usage rules
│   ├── constraints.py   # Read-only, safety, etc.
│   ├── modes.py         # Plan/auto mode prompts
│   └── efficiency.py    # Output efficiency
├── templates/
│   ├── base.yaml        # Default template
│   ├── explore.yaml     # Explore subagent
│   ├── plan.yaml        # Plan subagent
│   └── security.yaml    # Security monitor
└── composer.py          # Template rendering
```

**Rationale**: 
- Matches Claude Code's modular approach
- Templates allow customization without code changes
- Components can be mixed/matched per context

**Alternatives considered**:
- Single file with conditionals → Hard to maintain, no customization
- Full YAML-based prompt system → Over-engineered for current needs

### D2: Subagent Architecture

**Decision**: Lightweight subagent system via `codepi/core/subagent.py`:
```python
class SubagentConfig:
    name: str
    system_prompt: str
    tools: list[str]  # Tool names (whitelist)
    read_only: bool = False
    max_turns: int = 10

class SubagentRunner:
    async def run(self, prompt: str) -> SubagentResult:
        # Spawns isolated agent session with restricted tools
        ...
```

**Built-in subagents**:
| Subagent | Tools | Read-only | Purpose |
|----------|-------|-----------|---------|
| explore | read, find, grep, ls, bash (readonly) | Yes | Codebase search |
| plan | read, find, grep, ls, bash (readonly) | Yes | Architecture design |
| security | N/A (classifier only) | N/A | Action evaluation |

**Rationale**: 
- Minimal overhead (reuses existing AgentSession)
- Clear separation of concerns
- Extension point for custom subagents

**Alternatives considered**:
- Full multi-agent orchestration → Over-engineered
- No subagents → Miss key Claude Code capability

### D3: Plan Mode Implementation

**Decision**: 5-phase workflow state machine:
```
Phase 1: UNDERSTAND    → Explore codebase, ask clarifying questions
Phase 2: DESIGN        → Create implementation plan
Phase 3: REVIEW        → User reviews and approves
Phase 4: FINALIZE      → Write plan to file
Phase 5: EXIT          → Return to normal mode
```

State stored in `AgentSession._plan_mode_state`:
```python
@dataclass
class PlanModeState:
    phase: int
    plan_file: str | None
    exploration_results: list[str]
    design_content: str | None
```

**Rationale**: 
- Matches Claude Code's plan mode exactly
- Clear phase transitions with validation
- User approval gate before implementation

### D4: Security Monitor Design

**Decision**: Rule-based classifier with ALLOW/BLOCK/ASK outcomes:
```python
@dataclass
class SecurityDecision:
    action: Literal["ALLOW", "BLOCK", "ASK"]
    reason: str
    risk_level: Literal["low", "medium", "high"]
```

**Block rules** (from claude-prompts.md):
1. Destructive: rm -rf, DROP TABLE, kill -9
2. Hard-to-reverse: git push --force, git reset --hard
3. Shared state: push, PR creation, external posting
4. Credential exposure: .env files, API keys in code

**Rationale**: 
- Simple rules cover 90% of risks
- No ML complexity needed
- Extensible via extensions

### D5: Auto Mode Design

**Decision**: Behavior modifier flag with guidelines injection:
```python
@dataclass  
class AutoModeConfig:
    enabled: bool = False
    max_iterations: int = 100
    require_approval_for: list[str] = field(default_factory=lambda: ["push", "pr"])
```

Auto mode prompts injected:
- "Execute immediately"
- "Minimize interruptions"
- "Prefer action over planning"
- "Make reasonable decisions"

**Rationale**: 
- Simple flag-based approach
- Works with existing AgentSession
- Clear user control

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Prompt bloat increases token usage | Lazy-load components, compaction-aware |
| Subagent spawning latency | Cache subagent sessions, parallel spawning |
| Plan mode UX friction | Clear phase indicators, easy exit |
| Security monitor false positives | Tunable sensitivity, easy override |
| Auto mode runaway | Max iteration limit, periodic checkpoints |
| Breaking extension interface | Default implementations, deprecation path |

## Migration Plan

1. **Phase 1**: Add prompt module (backward compatible)
   - `AgentSession.system_prompt` becomes `AgentSession._prompt_config`
   - Property accessor maintains backward compatibility

2. **Phase 2**: Add subagent framework
   - New module, no existing code changes
   - Extensions can register custom subagents

3. **Phase 3**: Add modes (plan, auto)
   - New state fields in AgentSession
   - Mode activation via CLI flags or commands

4. **Phase 4**: Add security monitor
   - Optional, enabled via config
   - Can be disabled for trusted environments

**Rollback**: Each phase is independent. Disable via config flags.

## Open Questions

1. **Prompt template format**: YAML vs TOML? (Leaning: YAML for multiline strings)
2. **Subagent isolation level**: Same process vs subprocess? (Leaning: Same process for simplicity)
3. **Security monitor placement**: Pre-tool-call vs post-tool-call? (Leaning: Pre-tool-call)
4. **Plan file location**: `.codepi/plans/` vs user-specified? (Leaning: User-specified with default)
