## Why

codepi's RPC mode uses an ad-hoc JSONL protocol over stdio with no capability negotiation, no handshake, and no standard structure. This locks it to custom integrations only. Migrating to the [Agent Client Protocol (ACP)](https://agentclientprotocol.com/) standard enables interoperability with any ACP-compatible editor/IDE (Zed, JetBrains, VS Code extensions, etc.) and provides a proper JSON-RPC 2.0 transport layer with capability negotiation. This is Phase 1 of a 4-phase migration, focused on the transport and initialization foundation.

## What Changes

- **BREAKING**: Replace the custom JSONL RPC protocol in `codepi/modes/rpc.py` with ACP's JSON-RPC 2.0 transport
- Add `agent-client-protocol` Python SDK as a project dependency
- Create `codepi/acp/` package with the core agent class (`CodepiAgent`) that implements ACP's `Agent` base class
- Implement the `initialize` handshake: client sends protocol version + capabilities, agent responds with its capabilities and info
- Implement `new_session` stub: creates session ID, returns available modes (ask/code/plan/auto)
- The `--rpc` CLI flag continues to work — only the wire protocol changes
- Session/prompt/cancel/load_session methods are stubbed with `NotImplementedError` for Phase 2+ implementation

## Capabilities

### New Capabilities
- `acp-transport`: ACP JSON-RPC 2.0 transport layer over stdio, including the `initialize` handshake, `initialized` notification, and clean shutdown on stdin EOF
- `acp-agent`: `CodepiAgent` class implementing the ACP `Agent` base class with `initialize()`, `new_session()`, and stubbed prompt/cancel/load_session methods

### Modified Capabilities
<!-- No existing specs are affected — RPC mode has no prior spec coverage -->

## Impact

- **New dependency**: `agent-client-protocol>=0.1.0` in `pyproject.toml`
- **New files**: `codepi/acp/__init__.py`, `codepi/acp/agent.py`
- **Modified files**: `codepi/modes/rpc.py` (complete rewrite of entry point)
- **Breaking**: External consumers of the custom JSONL protocol must migrate to ACP client SDK
- **No changes** to interactive mode, print mode, SDK mode, or core AgentSession
