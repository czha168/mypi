## Context

codepi's auto-compaction system triggers when token usage exceeds a configurable percentage of the context window. The threshold is currently set to 0.80 (80%) by default in four locations across `config.py` and `agent_session.py`. The threshold is already user-configurable via `~/.codepi/config.toml` under `[session] compaction_threshold`.

## Goals / Non-Goals

**Goals:**
- Change the default `compaction_threshold` from 0.80 to 0.50 so compaction triggers earlier
- Keep all existing configurability intact (TOML config, constructor parameter, environment)
- Update documentation to reflect the new default

**Non-Goals:**
- Adding new configuration mechanisms (CLI flag, env var) — already configurable via TOML
- Changing the compaction algorithm itself
- Changing the tiered compaction format or LLM prompt
- Migration path for existing user configs (no breaking change — explicit configs override defaults)

## Decisions

### 1. Change all four default definition sites simultaneously

**Decision**: Update `0.80` → `0.50` in all four locations at once:
- `DEFAULT_CONFIG` TOML template string (line 16)
- `SessionConfig` dataclass field default (line 63)
- `load_config()` fallback value (line 160)
- `AgentSession.__init__` parameter default (line 57)

**Rationale**: Keeping defaults in sync across all sites prevents subtle bugs where one site uses a different default. This is a simple find-and-replace.

**Alternative considered**: Only change the `DEFAULT_CONFIG` template and let the others inherit. Rejected — Python defaults in dataclasses and function signatures don't inherit from TOML; they must be explicit.

### 2. Update existing test that hardcodes 0.80

**Decision**: Update `test_compaction_runs_when_threshold_exceeded` in `tests/core/test_agent_session.py` to use the new default (0.50) or explicitly pass 0.80 if testing a specific threshold scenario.

**Rationale**: The test explicitly passes `compaction_threshold=0.80` which is fine for that specific test case. No change needed unless we want to test the default path.

## Risks / Trade-offs

- **[More frequent compaction]** → Compaction at 50% means the model summarizes conversations earlier and more often. This uses extra LLM calls for summarization. Mitigation: the threshold is configurable — users who prefer the old behavior can set `compaction_threshold = 0.80` in their config.
- **[Token cost]** → More frequent compaction = more summarization LLM calls = slightly higher token usage. Mitigation: summarization prompts are small compared to full conversation context; the trade-off favors response quality.
- **[User surprise]** → Existing users relying on the default may notice compaction happening sooner. Mitigation: this is a behavioral improvement, not a regression. Document the change in README.
