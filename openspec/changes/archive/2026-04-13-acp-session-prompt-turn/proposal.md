## Why

Phase 1 established the ACP transport layer and `CodepiAgent` skeleton with `initialize`/`new_session` stubs. The `prompt` and `cancel` methods currently raise `NotImplementedError`. Without session/prompt flow, the ACP agent cannot execute any user requests — it is a shell that can shake hands but cannot act. Phase 2 bridges codepi's `AgentSession` turn loop to ACP's `session/prompt` → `session/update` notification lifecycle, making the agent functional.

## What Changes

- **New file**: `codepi/acp/session_adapter.py` — `ACPSessionAdapter` class that owns an `AgentSession` and bridges its callbacks (`on_token`, `on_tool_call`, `on_tool_result`, `on_error`) to ACP `session/update` notifications via `Client.session_update()`.
- **New file**: `codepi/acp/content.py` — Helper functions for building ACP `ContentBlock` dicts (text, resource, diff, terminal).
- **Modified**: `codepi/acp/agent.py` — Replace `prompt`/`cancel` stubs with real implementations that delegate to `ACPSessionAdapter`. `new_session` now creates an adapter and stores it in `_sessions` (not just a dict). Store `cwd` on adapter for lazy `AgentSession` init.
- **Modified**: `codepi/core/agent_session.py` — Add `cancel()` method and `is_cancelled` property to enable real cancellation of in-flight turns. Add `_cancelled` flag reset on `prompt()` entry.

## Capabilities

### New Capabilities
- `acp-session-adapter`: Bridges AgentSession callbacks to ACP session/update notifications — token streaming, tool call lifecycle, error reporting, and prompt turn management.
- `acp-content-blocks`: Helper module for constructing ACP ContentBlock dicts (text, resource, diff, terminal).

### Modified Capabilities
- `acp-agent`: The `prompt`, `cancel`, and `new_session` methods change from stubs to real implementations delegating to `ACPSessionAdapter`.

## Impact

- **Files**: 2 new files (`session_adapter.py`, `content.py`), 2 modified files (`agent.py`, `agent_session.py`)
- **Dependencies**: Relies on Phase 1 (`codepi/acp/agent.py`, `codepi/modes/rpc.py`) already complete
- **APIs**: `AgentSession` gains `cancel()` method and `is_cancelled` property — no breaking change to existing callers
- **Testing**: New unit tests for `ACPSessionAdapter` callback mapping; integration test for full `initialize → session/new → session/prompt → notifications → response` lifecycle
