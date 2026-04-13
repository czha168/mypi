## MODIFIED Requirements

### Requirement: Prompt stub raises NotImplementedError
The `prompt` method SHALL delegate to the `ACPSessionAdapter.run_prompt()` method for the given session. It SHALL return the `PromptResponse` from the adapter. If the session ID is unknown, it SHALL raise a `ValueError`.

#### Scenario: Calling prompt with valid session
- **WHEN** client sends `session/prompt` with a valid `session_id` and prompt blocks `[{"type": "text", "text": "Hello"}]`
- **THEN** agent SHALL delegate to the adapter's `run_prompt()` method
- **AND** return the resulting `PromptResponse` with appropriate `stop_reason`

#### Scenario: Calling prompt with unknown session
- **WHEN** client sends `session/prompt` with an unknown `session_id`
- **THEN** agent SHALL raise `ValueError` indicating the session is unknown

### Requirement: Cancel stub raises NotImplementedError
The `cancel` method SHALL delegate to the `ACPSessionAdapter.cancel()` method for the given session. If the session ID is unknown, it SHALL log a warning and return without error.

#### Scenario: Cancelling an active session
- **WHEN** client sends `session/cancel` notification with a valid `session_id`
- **THEN** agent SHALL call the adapter's `cancel()` method
- **AND** the adapter SHALL signal the in-flight turn to stop

#### Scenario: Cancelling an unknown session
- **WHEN** client sends `session/cancel` with an unknown `session_id`
- **THEN** agent SHALL log a warning and return without raising an error

### Requirement: new_session returns session ID and modes
The system SHALL implement `new_session(cwd, mcp_servers)` to create a new session. It SHALL create an `ACPSessionAdapter` with the session ID, cwd, config, and client connection. It SHALL store the adapter in `_sessions` and return a `NewSessionResponse` with a unique session ID and the list of available modes.

#### Scenario: Successful session creation
- **WHEN** client sends `session/new` with `cwd: "/tmp/project"`
- **THEN** agent SHALL create an `ACPSessionAdapter(session_id, cwd, config, conn)` 
- **AND** store it in `_sessions[session_id]`
- **AND** return a `NewSessionResponse` with a unique `session_id` (UUID format)
- **AND** `modes.current_mode_id` SHALL be `"code"`
- **AND** `modes.available_modes` SHALL contain 4 modes: ask, code, plan, auto
