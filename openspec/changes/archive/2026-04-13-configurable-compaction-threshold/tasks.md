## 1. Update Default Values in Code

- [x] 1.1 Change `compaction_threshold` default from `0.80` to `0.50` in `codepi/config.py` `DEFAULT_CONFIG` TOML template (line 16)
- [x] 1.2 Change `compaction_threshold` default from `0.80` to `0.50` in `codepi/config.py` `SessionConfig` dataclass (line 63)
- [x] 1.3 Change `compaction_threshold` fallback from `0.80` to `0.50` in `codepi/config.py` `load_config()` (line 160)
- [x] 1.4 Change `compaction_threshold` default from `0.80` to `0.50` in `codepi/core/agent_session.py` `AgentSession.__init__` (line 57)

## 2. Update Documentation

- [x] 2.1 Update `README.md` Auto-compaction section to say "50%" instead of "80%"
- [x] 2.2 Update `README.md` config example `[session] compaction_threshold = 0.50`

## 3. Verify

- [x] 3.1 Run `pytest tests/core/test_agent_session.py` — existing tests pass
- [x] 3.2 Run `pytest tests/core/test_tiered_compaction.py` — existing tests pass
- [x] 3.3 Grep for any remaining `0.80` references to `compaction_threshold` in the codebase
