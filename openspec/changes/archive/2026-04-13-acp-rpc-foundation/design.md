## Context

codepi's RPC mode (`codepi/modes/rpc.py`, 97 lines) uses a custom JSONL protocol over stdio with 6 command types (`prompt`, `steer`, `follow_up`, `cancel`, `exit`, `get-session-id`) and plain-JSON responses (`token`, `tool_call`, `tool_result`, `error`, `done`, `cancelled`, `id`). There is no handshake, no capability negotiation, and no JSON-RPC envelope.

The [Agent Client Protocol (ACP)](https://agentclientprotocol.com/) is a standard backed by Zed Industries that defines a JSON-RPC 2.0 protocol for editor↔agent communication. The official Python SDK (`agent-client-protocol` v0.9.0) provides an `Agent` Protocol, `run_agent()` entry point, Pydantic schema types, and helper builders.

**Current codebase constraints**:
- `RPCMode.__init__` receives pre-built `provider`, `session_manager`, `model`, `tool_registry`, `extensions`, `skill_loader` — and wires them into `AgentSession`
- Config is loaded in `__init__` via `load_config()` to optionally add `MemoryExtension`
- `_emit()` writes JSON synchronously to stdout
- `run()` reads from `asyncio.StreamReader` over stdin

**ACP SDK architecture** (from research):
- `Agent` is a **Protocol** (duck-typed interface, not a base class)
- `on_connect(conn: Client)` receives the client connection for sending notifications
- `run_agent(agent)` handles the JSON-RPC transport loop
- Helper functions: `text_block()`, `update_agent_message()`, `start_tool_call()`, etc.

## Goals / Non-Goals

**Goals:**
- Replace the custom JSONL transport with ACP's JSON-RPC 2.0 over stdio
- Implement the `initialize` handshake with proper capability negotiation
- Implement `new_session` stub that returns session ID and available modes
- Stub `prompt`, `cancel`, `load_session` methods with clear Phase 2 markers
- Keep `--rpc` CLI flag unchanged — only the wire protocol changes
- Zero impact on interactive, print, and SDK modes

**Non-Goals:**
- Session/prompt turn implementation (Phase 2)
- Tool call lifecycle, permission requests, diff content (Phase 3)
- Session loading, mode switching, extension methods (Phase 4)
- MCP server support
- Backward compatibility with the old JSONL protocol

## Decisions

### Decision 1: Use ACP Python SDK directly (not vendor the protocol)

**Choice**: `pip install agent-client-protocol>=0.1.0`

**Rationale**: The SDK (v0.9.0, Apache-2.0) is actively maintained by the official `agentclientprotocol` org with 6.6M monthly downloads. It provides Pydantic schema types, JSON-RPC transport, and helper builders. Vendoring would duplicate effort and drift from spec updates.

**Alternative considered**: Implement JSON-RPC 2.0 ourselves. Rejected because the SDK handles edge cases (batching, error codes, notification vs request) and generates types from the spec.

### Decision 2: CodepiAgent as a class satisfying the Agent Protocol

**Choice**: `CodepiAgent` implements the `Agent` Protocol methods (`initialize`, `new_session`, `prompt`, `cancel`, `load_session`, `on_connect`) as a concrete class.

**Rationale**: The ACP SDK's `Agent` is a `Protocol` (structural typing). We write a class that satisfies it, following the pattern from the SDK's `examples/echo_agent.py`. The `on_connect` method stores the `Client` connection for future notification sending.

### Decision 3: Config loaded in RPCMode, passed to CodepiAgent

**Choice**: `RPCMode.__init__` loads config via `load_config()` and passes the `Config` object to `CodepiAgent`. `CodepiAgent.__init__` accepts `config: Config`.

**Rationale**: This matches the current pattern where `RPCMode` handles setup and delegates to the session. Config loading stays in the mode layer; the agent receives ready-to-use configuration. This also keeps `CodepiAgent` testable with injected configs.

### Decision 4: Minimal AgentSession changes in Phase 1

**Choice**: No changes to `AgentSession` in Phase 1. The session/prompt bridge (`ACPSessionAdapter`) is Phase 2 work.

**Rationale**: Phase 1 is transport-only. AgentSession's callback interface (`on_token`, `on_tool_call`, `on_tool_result`, `on_error`) and `_emit` pattern won't be touched until we wire them to ACP notifications in Phase 2.

### Decision 5: Stub methods raise NotImplementedError with clear Phase markers

**Choice**: `prompt()`, `cancel()`, `load_session()` on `CodepiAgent` raise `NotImplementedError("Phase 2")` / `NotImplementedError("Phase 4")`.

**Rationale**: Makes the API surface visible for testing and IDE navigation while clearly marking what's incomplete. The ACP SDK will return a JSON-RPC error to the client, which is the correct behavior for unimplemented methods.

## Risks / Trade-offs

- **[ACP SDK API stability]** → Pin `>=0.1.0,<1.0`. The SDK is at v0.9.0 and closely tracks the spec. If breaking changes occur, we can vendor the specific version.
- **[Breaking change for existing RPC consumers]** → No backward compatibility. The RPC mode is an integration point, not user-facing. Document the migration path (use ACP client SDK).
- **[Async callback ordering]** → Phase 1 doesn't bridge callbacks, so no ordering concern yet. Phase 2 will use `asyncio.create_task()` carefully.
- **[Agent Protocol is duck-typed]** → No compile-time checking that we satisfy the protocol. Mitigation: unit tests verify all required methods exist and return correct types.
