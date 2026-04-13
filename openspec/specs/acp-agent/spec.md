## ADDED Requirements

### Requirement: CodepiAgent class implements Agent Protocol
The system SHALL provide a `CodepiAgent` class that satisfies the ACP `Agent` Protocol interface. The class SHALL implement `on_connect`, `initialize`, `new_session`, and provide stub implementations for `prompt`, `cancel`, and `load_session`.

#### Scenario: CodepiAgent satisfies Agent Protocol
- **WHEN** `CodepiAgent` is instantiated with a `Config` object
- **THEN** it SHALL have methods `on_connect`, `initialize`, `new_session`, `prompt`, `cancel`, `load_session`

### Requirement: Config injection into CodepiAgent
`CodepiAgent` SHALL accept a `Config` object at construction time. The config SHALL be used to create providers, session managers, and tool registries when sessions are created.

#### Scenario: Config is stored and accessible
- **WHEN** `CodepiAgent(config=some_config)` is constructed
- **THEN** the config SHALL be stored for use in `new_session` and later phases

### Requirement: Client connection via on_connect
`CodepiAgent` SHALL implement `on_connect(conn)` to receive the ACP `Client` connection object. This connection SHALL be stored for sending `session/update` notifications in Phase 2.

#### Scenario: Connection stored after on_connect
- **WHEN** ACP transport calls `agent.on_connect(conn)` with a Client connection
- **THEN** the agent SHALL store the connection for later use

### Requirement: new_session returns session ID and modes
The system SHALL implement `new_session(cwd, mcp_servers)` to create a new session. It SHALL return a `NewSessionResponse` with a unique session ID and the list of available modes: ask, code, plan, auto.

#### Scenario: Successful session creation
- **WHEN** client sends `session/new` with `cwd: "/tmp/project"`
- **THEN** agent SHALL return a `NewSessionResponse` with a unique `session_id` (UUID format)
- **AND** `modes.current_mode_id` SHALL be `"code"`
- **AND** `modes.available_modes` SHALL contain 4 modes: ask, code, plan, auto

#### Scenario: Multiple sessions tracked
- **WHEN** client creates two sessions via `session/new`
- **THEN** both sessions SHALL be tracked in the agent's internal session map with distinct session IDs

### Requirement: Available modes declaration
The agent SHALL declare 4 available modes: "Ask" (read-only, id=ask), "Code" (full tools, id=code), "Plan" (structured planning, id=plan), "Auto" (continuous execution, id=auto). The default mode SHALL be "code".

#### Scenario: Modes in new_session response
- **WHEN** client receives `new_session` response
- **THEN** `modes.available_modes` SHALL contain exactly 4 entries with ids: "ask", "code", "plan", "auto"
- **AND** `modes.current_mode_id` SHALL be `"code"`

### Requirement: Prompt stub raises NotImplementedError
The `prompt` method SHALL raise `NotImplementedError` to indicate Phase 2 work. The ACP transport SHALL convert this to a proper JSON-RPC error response.

#### Scenario: Calling prompt before Phase 2
- **WHEN** client sends `session/prompt` request
- **THEN** agent SHALL return a JSON-RPC error response indicating the method is not yet implemented

### Requirement: Cancel stub raises NotImplementedError
The `cancel` method SHALL raise `NotImplementedError` to indicate Phase 2 work.

#### Scenario: Calling cancel before Phase 2
- **WHEN** client sends `session/cancel` notification
- **THEN** agent SHALL handle the call without crashing (stub behavior)

### Requirement: Load session stub raises NotImplementedError
The `load_session` method SHALL raise `NotImplementedError` to indicate Phase 4 work.

#### Scenario: Calling load_session before Phase 4
- **WHEN** client sends `session/load` request
- **THEN** agent SHALL return a JSON-RPC error response indicating the method is not yet implemented
