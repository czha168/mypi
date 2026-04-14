## ADDED Requirements

### Requirement: Security ASK decisions trigger ACP permission requests
When the `SecurityMonitor` returns `SecurityAction.ASK` for a tool call, the system SHALL send a `session/request_permission` request to the ACP client via `Client.request_permission()`, and await the client's response before proceeding with or rejecting the tool execution.

#### Scenario: Bash command flagged as ASK
- **WHEN** a tool call for `bash` with command `git push` is evaluated by the security monitor
- **AND** the monitor returns `SecurityAction.ASK` with reason "Pushing to remote. Confirm?"
- **THEN** the system SHALL call `Client.request_permission()` with permission options including "Allow once", "Allow always", "Reject"
- **AND** the system SHALL await the client's response before executing the bash command

#### Scenario: Client approves the permission
- **WHEN** the client responds to `request_permission` with outcome `allowed`
- **THEN** the tool execution SHALL proceed normally
- **AND** the tool call notification SHALL continue with `status: "in_progress"`

#### Scenario: Client rejects the permission
- **WHEN** the client responds to `request_permission` with outcome `denied`
- **THEN** the tool execution SHALL be skipped
- **AND** the `on_tool_result` callback SHALL fire with a `ToolResult` containing `error` starting with "Rejected by user"

#### Scenario: Client does not respond (timeout)
- **WHEN** the client does not respond to `request_permission` within 120 seconds
- **THEN** the system SHALL treat the permission as denied
- **AND** log a warning about the permission timeout

### Requirement: Security BLOCK decisions bypass permission flow
When the `SecurityMonitor` returns `SecurityAction.BLOCK`, the system SHALL skip the permission flow entirely and immediately return a blocked tool result. No `request_permission` SHALL be sent to the client.

#### Scenario: Destructive command blocked
- **WHEN** a tool call for `bash` with command `rm -rf /` is evaluated by the security monitor
- **AND** the monitor returns `SecurityAction.BLOCK`
- **THEN** the system SHALL NOT send `request_permission` to the client
- **AND** the tool result SHALL contain an error starting with "Security:"

### Requirement: Security ALLOW decisions bypass permission flow
When the `SecurityMonitor` returns `SecurityAction.ALLOW`, the system SHALL skip the permission flow and execute the tool immediately.

#### Scenario: Safe command allowed
- **WHEN** a tool call for `bash` with command `ls -la` is evaluated by the security monitor
- **AND** the monitor returns `SecurityAction.ALLOW`
- **THEN** the system SHALL NOT send `request_permission` to the client
- **AND** the tool execution SHALL proceed immediately

### Requirement: Permission options include standard choices
The system SHALL offer four permission options in every `request_permission` call: "Allow once", "Allow always", "Reject once", "Reject always".

#### Scenario: Permission options sent to client
- **WHEN** a permission request is sent to the client
- **THEN** the `options` parameter SHALL contain exactly four `PermissionOption` entries
- **AND** the options SHALL have `kind` values: `allow_once`, `allow_always`, `reject_once`, `reject_always`

### Requirement: Permission request includes tool call context
The `request_permission` call SHALL include a `ToolCallUpdate` with the tool call's ID, kind, status ("pending"), and title describing the operation.

#### Scenario: Permission request with tool context
- **WHEN** a permission request is sent for tool call `call_3` (`bash`, command `git push`)
- **THEN** the `tool_call` parameter SHALL have `toolCallId: "call_3"`, `kind: "execute"`, `status: "pending"`
- **AND** the `title` SHALL describe the operation being requested
