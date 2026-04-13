## Context

Phase 1 (`acp-transport` + `acp-agent` specs) established the ACP JSON-RPC transport layer and a `CodepiAgent` class skeleton. The agent can respond to `initialize` and `session/new` requests, but `prompt` and `cancel` raise `NotImplementedError`. The existing `AgentSession` class drives the LLM turn loop with sync callbacks (`on_token`, `on_tool_call`, `on_tool_result`, `on_error`) designed for the interactive TUI.

The gap: `AgentSession` emits events through sync callbacks to a TUI that renders them immediately. ACP requires these same events to be sent as async `session/update` notifications over a JSON-RPC connection. We need a bridge.

**ACP SDK key API** (from `agent-client-protocol` v0.9.0):
- `self._conn.session_update(session_id, update)` — async, sends a `session/update` notification
- Helper builders: `update_agent_message(text_block(...))`, `start_tool_call(...)`, `update_tool_call(...)`
- `PromptResponse(stop_reason="end_turn"|"cancelled"|"refusal"|"max_tokens")`
- `cancel()` is a notification (no response expected) — agent should stop in-flight work

**Current code constraints**:
- `AgentSession` callbacks are sync (`Callable[[str], None]`), not async
- `AgentSession._stream_turn()` is the core loop that processes LLM events, calls tools, and fires callbacks
- No cancellation mechanism exists in `AgentSession` — the `cancel` command in the old RPC mode only emitted an event without actual abort

## Goals / Non-Goals

**Goals:**
- Bridge `AgentSession` callbacks to ACP `session/update` notifications via `Client.session_update()`
- Implement `CodepiAgent.prompt()` to run a full LLM turn and return `PromptResponse` with correct `stop_reason`
- Implement `CodepiAgent.cancel()` to signal cancellation of an in-flight turn
- Support the full tool call lifecycle: `tool_call_start` → tool execution → `tool_call_update` with status
- Stream LLM tokens as `agent_message_chunk` notifications in real time
- Map codepi tool names to ACP `ToolKind` values (read, edit, execute, search, other)
- Add cancellation support to `AgentSession` via a `cancel()` method and `is_cancelled` property

**Non-Goals:**
- Permission requests via `session/request_permission` (Phase 3)
- Diff content for write/edit tools (Phase 3)
- Session loading and history replay (Phase 4)
- Mode switching via `session/set_mode` (Phase 4)
- MCP server integration
- Image/audio content block handling

## Decisions

### Decision 1: Use `asyncio.create_task()` to bridge sync callbacks to async notifications

`AgentSession` callbacks are synchronous (`Callable[[str], None]`). ACP's `session_update()` is async. Rather than refactoring `AgentSession` to use async callbacks (which would cascade through the TUI and all callers), we bridge at the adapter layer.

**Approach**: Each sync callback in `ACPSessionAdapter` wraps `asyncio.create_task(self._send_update(...))` to schedule the async notification without blocking the sync callback path.

**Alternative considered**: Make `AgentSession` callbacks async (`Callable[[str], Coroutine]`). Rejected because it would require changing the TUI layer, all modes, and the callback invocation points in `_stream_turn()` — too invasive for a bridging layer.

**Trade-off**: `create_task` provides fire-and-forget semantics with no backpressure. If the ACP client is slow, tasks queue in the event loop. This is acceptable because JSON-RPC over stdio is local and fast; network latency is not a concern.

### Decision 2: Lazy initialization of AgentSession in adapter

`ACPSessionAdapter` defers creating `AgentSession`, `SessionManager`, `LLMProvider`, and `ToolRegistry` until the first `prompt()` call. The `new_session` handler only records `session_id` and `cwd`.

**Rationale**: `new_session` is lightweight — it doesn't need an LLM connection. Lazy init avoids creating providers/registries for sessions that never receive a prompt. It also means we don't need to pass the config deep into the adapter constructor.

### Decision 3: Cancellation via flag, not `asyncio.Task.cancel()`

Add a `_cancelled` boolean flag to `AgentSession`. The `cancel()` method sets this flag. The `_stream_turn()` loop checks the flag between iterations (after each tool result) and breaks if set.

**Alternative considered**: Use `asyncio.Task.cancel()` to raise `CancelledError` in the running turn. Rejected because:
1. `CancelledError` can be raised at any `await` point, making cleanup unpredictable
2. Tool execution (file writes, shell commands) could be interrupted mid-operation, leaving partial state
3. The flag approach gives us a clean checkpoint between tool calls — the current tool finishes, but no new tool starts

**Trade-off**: Cancellation is not instant — it takes effect at the next tool call boundary. For LLM token streaming, tokens continue until the LLM finishes its response or a tool call starts. This is acceptable because the LLM turn is typically short compared to tool execution time.

### Decision 4: Tool call ID counter per adapter

Each `ACPSessionAdapter` maintains its own monotonically increasing integer counter for tool call IDs (`call_1`, `call_2`, ...). The current tool call ID is stored in `_current_tool_call_id` so the `_on_tool_result` callback can reference it.

**Alternative considered**: Use UUIDs for tool call IDs. Rejected because they're harder to debug in logs and provide no ordering information. The integer counter is simpler and sufficient for a single-session adapter.

### Decision 5: Session data stored as adapter instances, not dicts

Change `CodepiAgent._sessions` from `dict[str, dict[str, Any]]` to `dict[str, ACPSessionAdapter]`. Each `new_session` creates an adapter immediately.

**Rationale**: Phase 1 stored dicts as placeholders. Phase 2 needs real objects to handle prompts. The adapter IS the session state — it owns the `AgentSession`, tracks tool call IDs, and manages cancellation.

## Risks / Trade-offs

| Risk | Impact | Mitigation |
|------|--------|------------|
| Callback ordering not guaranteed with `create_task` | Notifications may arrive out of order if multiple fire simultaneously | Each callback creates at most one task; `create_task` schedules in FIFO order on the event loop. In practice, callbacks are sequential (token → token → ... → tool_call → tool_result) |
| No backpressure on notification sending | Fast LLM streaming could queue many tasks | stdio transport is local; the kernel pipe buffer absorbs bursts. If needed, batch tokens in the adapter (future optimization) |
| Cancellation delay | Up to one full tool execution after cancel signal | Acceptable for local stdio use. Document the behavior. |
| `AgentSession` not designed for ACP | Some adaptations needed (cancel flag, callback signatures) | Minimal changes: only add `cancel()`/`is_cancelled` and `_cancelled` flag. No restructuring. |
| ACP SDK API stability | `agent-client-protocol` is v0.9.0, API may change | Pin version in `pyproject.toml`. The adapter layer isolates SDK types from codepi internals. |
