## MODIFIED Requirements

### Requirement: Tool call lifecycle mapped to ACP notifications
The system SHALL map `AgentSession.on_tool_call` to `ToolCallStart` notifications and `AgentSession.on_tool_result` to `ToolCallUpdate` notifications with the correct status (`in_progress` → `completed` or `failed`). Additionally, `write` and `edit` tool results SHALL include `FileEditToolCallContent` diff content when the result is successful, and the adapter SHALL use `tool_adapter.py` helper functions for diff extraction.

#### Scenario: Successful tool execution
- **WHEN** `AgentSession` fires `on_tool_call("read", {"path": "/tmp/file.py"})` then `on_tool_result("read", ToolResult(output="file contents"))`
- **THEN** the adapter SHALL send a `ToolCallStart` notification with `status: "in_progress"`, `kind: "read"`, and `locations: [{"path": "/tmp/file.py"}]`
- **AND** the adapter SHALL send a `ToolCallUpdate` notification with `status: "completed"` and text content containing the tool output

#### Scenario: Successful edit tool with diff content
- **WHEN** `AgentSession` fires `on_tool_call("edit", {"file_path": "/tmp/a.py", "old_string": "x", "new_string": "y"})` then `on_tool_result("edit", ToolResult(output="OK"))`
- **THEN** the adapter SHALL send a `ToolCallUpdate` notification with `status: "completed"`
- **AND** the notification SHALL include a `FileEditToolCallContent` with `path: "/tmp/a.py"`, `oldText: "x"`, `newText: "y"`

#### Scenario: Successful write tool with diff content
- **WHEN** `AgentSession` fires `on_tool_call("write", {"file_path": "/tmp/b.py", "content": "new"})` then `on_tool_result("write", ToolResult(output="OK"))`
- **THEN** the adapter SHALL send a `ToolCallUpdate` notification with `status: "completed"`
- **AND** the notification SHALL include a `FileEditToolCallContent` with `path: "/tmp/b.py"`, `oldText: None`, `newText: "new"`

#### Scenario: Failed tool execution
- **WHEN** `AgentSession` fires `on_tool_call("bash", {"command": "false"})` then `on_tool_result("bash", ToolResult(error="exit code 1"))`
- **THEN** the adapter SHALL send a `ToolCallStart` notification with `status: "in_progress"` and `kind: "execute"`
- **AND** the adapter SHALL send a `ToolCallUpdate` notification with `status: "failed"` and content containing the error message

#### Scenario: Tool call ID tracking
- **WHEN** `AgentSession` fires `on_tool_call` for the first time in a session
- **THEN** the adapter SHALL assign tool call ID `"call_1"`
- **WHEN** a second tool call fires in the same session
- **THEN** the adapter SHALL assign tool call ID `"call_2"`
- **AND** each `ToolCallUpdate` SHALL reference the corresponding tool call ID from the preceding `ToolCallStart`

## ADDED Requirements

### Requirement: Security ASK decisions routed through ACP permission flow
When the `SecurityMonitor` returns `SecurityAction.ASK` during a tool call, the adapter's `on_security_ask` callback SHALL call `Client.request_permission()` with the tool call context and permission options, and return the client's decision as a boolean. The adapter SHALL set this callback as the `AgentSession.on_security_ask` parameter during setup.

#### Scenario: Security ASK triggers permission request
- **WHEN** `AgentSession._stream_turn()` calls the `on_security_ask` callback with reason "Pushing to remote"
- **THEN** the callback SHALL call `self._conn.request_permission()` with the current tool call ID, kind, and permission options
- **AND** return `True` if the client approves, `False` if the client denies or times out

#### Scenario: Permission callback integrates with AgentSession setup
- **WHEN** `ACPSessionAdapter._setup()` is called
- **THEN** the adapter SHALL set `self._agent_session._on_security_ask` to the ACP permission callback
- **AND** the adapter SHALL create a `SecurityMonitor` with the config's security settings
- **AND** pass it to `AgentSession` as `security_monitor`
