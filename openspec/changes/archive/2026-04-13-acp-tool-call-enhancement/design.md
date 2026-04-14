## Context

Phase 1–2 of the ACP migration produced `codepi/acp/agent.py` and `codepi/acp/session_adapter.py`. The adapter currently maps `AgentSession` callbacks (`on_token`, `on_tool_call`, `on_tool_result`, `on_error`) to ACP notifications, but treats all tool calls uniformly — no permission checks, no diff content, and no enrichment of the tool call lifecycle.

codepi already has a `SecurityMonitor` (`codepi/core/security.py`) that classifies tool calls as ALLOW/BLOCK/ASK. In the interactive TUI, ASK decisions trigger a synchronous user prompt. In the ACP RPC context, this synchronous callback doesn't exist — the client is on the other end of a JSON-RPC pipe. We need ACP's `session/request_permission` to bridge this gap.

The ACP SDK provides `Client.request_permission(options, session_id, tool_call)` which returns a `RequestPermissionResponse` with an `outcome` discriminated union (`allowed` or `denied`).

## Goals / Non-Goals

**Goals:**
- Route `SecurityAction.ASK` decisions through ACP's `session/request_permission` so the editor client can approve/reject dangerous operations
- Enrich `tool_call_update` notifications for `write`/`edit` tools with `FileEditToolCallContent` (diff type) so editors can render inline diffs
- Extract helper logic (permission decisions, diff extraction, location extraction) into a focused `tool_adapter.py` module to keep `session_adapter.py` focused on the notification bridge
- Preserve the existing tool kind mapping and location extraction (already working)

**Non-Goals:**
- Terminal delegation via ACP (`terminal/create`, etc.) — deferred to future work
- File system delegation via ACP (`fs/read_text_file`, etc.) — deferred to future work
- MCP server integration — deferred to Phase 4
- Changing the interactive TUI's security handling — only RPC mode is affected

## Decisions

### Decision 1: Permission flow hooks into AgentSession's `_on_security_ask` callback

**Choice**: Instead of modifying `AgentSession._stream_turn()` to be async-aware for ACP, we inject an `on_security_ask` callback into `AgentSession` that calls `Client.request_permission()`.

**Rationale**: `AgentSession` already has an `on_security_ask` parameter (used by TUI for synchronous prompts). The ACP adapter simply provides a different implementation — one that calls `self._conn.request_permission()` asynchronously. This avoids touching `AgentSession` internals and keeps the adapter pattern clean.

**Alternative considered**: Intercept at the `_on_tool_call` callback level and inject a pre-execution check. Rejected because tool call callbacks fire *after* the tool has already been dispatched by `AgentSession._stream_turn()`. The security check happens inside `_stream_turn()` before tool execution, so we must hook into the same point.

### Decision 2: Diff content extracted from tool arguments, not from reading the file

**Choice**: For `edit` tool, use `old_string` and `new_string` from arguments directly. For `write` tool, use `content` from arguments with `old_text=None`.

**Rationale**: Reading the file before/after adds I/O overhead and race conditions. The arguments already contain all the information needed for a diff display. `old_text=None` for `write` is semantically correct — it's a full file replacement, and the ACP spec supports `oldText` being absent for new files.

**Alternative considered**: Read the file before writing to capture old content. Rejected due to: (a) race conditions, (b) double I/O, (c) `edit` tool already provides both old and new strings.

### Decision 3: `tool_adapter.py` as a pure function module (no classes)

**Choice**: Extract permission logic, diff extraction, and tool kind mapping into standalone functions in `tool_adapter.py`. No adapter class needed.

**Rationale**: These are all pure data transformations (tool name → kind, arguments → diff content, security decision → permission request). A class would add unnecessary state management. The `session_adapter.py` imports and calls these functions as needed.

**Alternative considered**: Make `ToolAdapter` a class that wraps the tool call lifecycle. Rejected as over-engineering — the functions have no shared state.

## Risks / Trade-offs

- **[Async callback in sync context]** → The `on_security_ask` callback in `AgentSession` is called synchronously, but `Client.request_permission()` is async. **Mitigation**: Use `asyncio.run_coroutine_threadsafe()` or restructure so the callback returns a coroutine that `_stream_turn` awaits. Actually, looking at the code, `_stream_turn` is already async and calls `self._on_security_ask` synchronously — we need to change this to `await` if the callback is async. **Better approach**: Make `AgentSession` accept an async `on_security_ask` callback and `await` it in `_stream_turn`. This is a minimal change (one `await` addition).

- **[Permission timeout]** → Client never responds to `request_permission` → tool execution hangs. **Mitigation**: Add a timeout (e.g., 120s) to the permission request; if it times out, treat as denied.

- **[Diff accuracy for write tool]** → `write` tool replaces entire file, so `old_text=None` means the editor can't show a meaningful diff. **Mitigation**: Accept this limitation for now; editors typically handle `oldText=None` gracefully by showing the full new content. Future enhancement could read the file before writing.

- **[Backward compatibility]** → Changing `on_security_ask` from sync to async callback signature breaks any existing callers. **Mitigation**: The only existing caller is the TUI's security handler, which can be trivially wrapped in an async function. Check before merging.
