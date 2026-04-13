## 1. Dependency & Package Setup

- [x] 1.1 Add `agent-client-protocol>=0.1.0` to `pyproject.toml` dependencies
- [x] 1.2 Install the dependency in the venv: `pip3 install agent-client-protocol`
- [x] 1.3 Verify import works: `python3 -c "from acp import Agent, run_agent; print('OK')"`

## 2. ACP Package Scaffold

- [x] 2.1 Create `codepi/acp/__init__.py` with package exports (`CodepiAgent`)
- [x] 2.2 Create `codepi/acp/agent.py` with `CodepiAgent` class skeleton:
  - `__init__(self, config: Config)` — store config
  - `on_connect(self, conn)` — store ACP Client connection
  - `initialize(...)` → return `InitializeResponse` with capabilities and agent info
  - `new_session(cwd, mcp_servers)` → return `NewSessionResponse` with UUID session ID + 4 modes
  - `prompt(...)` → raise `NotImplementedError("Phase 2: session/prompt not yet implemented")`
  - `cancel(...)` → raise `NotImplementedError("Phase 2: session/cancel not yet implemented")`
  - `load_session(...)` → raise `NotImplementedError("Phase 4: session/load not yet implemented")`

## 3. RPC Mode Replacement

- [x] 3.1 Replace `codepi/modes/rpc.py` with ACP entry point:
  - `RPCMode.__init__(**kwargs)` — load config via `load_config()`, store it
  - `RPCMode.run(reader=None)` — create `CodepiAgent(config)`, call `run_agent(agent)`
- [x] 3.2 Verify the `--rpc` CLI flag still works (loads mode, doesn't crash on startup)

## 4. Verification

- [x] 4.1 Unit test: `CodepiAgent.initialize()` returns correct `protocolVersion`, `agentCapabilities`, `agentInfo`, empty `authMethods`
- [x] 4.2 Unit test: `CodepiAgent.new_session()` returns UUID `session_id` and 4 modes (ask/code/plan/auto) with `current_mode_id="code"`
- [x] 4.3 Unit test: `CodepiAgent.prompt()` raises `NotImplementedError`
- [x] 4.4 Unit test: `CodepiAgent.on_connect()` stores the connection object
- [x] 4.5 Integration test: launch `codepi --rpc` as subprocess, send `initialize` JSON-RPC request, verify valid response with correct capabilities
- [x] 4.6 Integration test: send `initialize` then `session/new`, verify session ID returned and modes are present
- [x] 4.7 Integration test: verify clean exit on stdin EOF
- [x] 4.8 Regression test: `codepi` (interactive mode) still launches normally after changes
