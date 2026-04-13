## Why

The compaction threshold determines when auto-compaction triggers — currently at 80% of the context window. This is too aggressive for longer sessions: the model operates near capacity for too long, leading to degraded response quality before compaction kicks in. Lowering the default to 50% triggers compaction earlier, keeping the conversation lean and responses higher quality. The threshold is already configurable via `config.toml`; this change only adjusts the default value.

## What Changes

- Change the default `compaction_threshold` from `0.80` (80%) to `0.50` (50%) across all definition sites:
  - `SessionConfig` dataclass default
  - `AgentSession.__init__` parameter default
  - `DEFAULT_CONFIG` TOML template string
  - `load_config()` fallback value
- Update README documentation mentioning the 80% threshold

## Capabilities

### New Capabilities

_None_

### Modified Capabilities

_None_

## Impact

- **Code**: `codepi/config.py` (3 locations), `codepi/core/agent_session.py` (1 location)
- **Docs**: `README.md` (Auto-compaction section mentions "80%")
- **Tests**: Existing `test_agent_session.py` compaction test uses explicit `compaction_threshold=0.80` — no breakage, but should be updated to match new default
- **User config**: No breaking change — users with explicit `compaction_threshold` in their `config.toml` are unaffected. Only users relying on the default will see the new behavior.
