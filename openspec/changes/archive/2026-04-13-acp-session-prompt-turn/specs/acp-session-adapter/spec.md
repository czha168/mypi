## ADDED Requirements

### Requirement: ACPSessionAdapter bridges AgentSession to ACP notifications
The system SHALL provide an `ACPSessionAdapter` class that owns an `AgentSession` and translates its sync callbacks to ACP `session/update` notifications. The adapter SHALL be created when `CodepiAgent.new_session()` is called and stored for the session's lifetime.

#### Scenario: Adapter created on new_session
- **WHEN** client sends `session/new` with `cwd: "/tmp/project"`
- **THEN** `CodepiAgent` SHALL create an `ACPSessionAdapter` with the session ID, cwd, config, and client connection
- **AND** the adapter SHALL be stored in `_sessions[session_id]`

#### Scenario: Adapter not yet initialized on new_session
- **WHEN** `ACPSessionAdapter` is constructed
- **THEN** it SHALL NOT create `AgentSession`, `LLMProvider`, `SessionManager`, or `ToolRegistry` until the first `prompt()` call

### Requirement: LLM token streaming as agent_message_chunk
The system SHALL wire `AgentSession.on_token` callback to send `agent_message_chunk` `session/update` notifications. Each token received from the LLM SHALL be forwarded to the ACP client as a text content block.

#### Scenario: Streaming tokens to client
- **WHEN** `AgentSession` fires `on_token("Hello")` during a prompt turn
- **THEN** the adapter SHALL send a `session/update` notification with `agent_message_chunk` containing `{"type": "text", "text": "Hello"}`

#### Scenario: Multiple tokens in sequence
- **WHEN** `AgentSession` fires `on_token("He")` then `on_token("llo")` in rapid succession
- **THEN** two separate `session/update` notifications SHALL be sent, one for each token
- **AND** the notifications SHALL be sent in the same order as the callbacks fired

### Requirement: Tool call lifecycle mapped to ACP notifications
The system SHALL map `AgentSession.on_tool_call` to `start_tool_call` notifications and `AgentSession.on_tool_result` to `update_tool_call` notifications with the correct status (`in_progress` → `completed` or `failed`).

#### Scenario: Successful tool execution
- **WHEN** `AgentSession` fires `on_tool_call("read", {"path": "/tmp/file.py"})` then `on_tool_result("read", ToolResult(output="file contents"))` 
- **THEN** the adapter SHALL send a `start_tool_call` notification with `status: "in_progress"`, `kind: "read"`, and `locations: [{"path": "/tmp/file.py"}]`
- **AND** the adapter SHALL send an `update_tool_call` notification with `status: "completed"` and text content containing the tool output

#### Scenario: Failed tool execution
- **WHEN** `AgentSession` fires `on_tool_call("bash", {"command": "false"})` then `on_tool_result("bash", ToolResult(error="exit code 1"))`
- **THEN** the adapter SHALL send a `start_tool_call` notification with `status: "in_progress"` and `kind: "execute"`
- **AND** the adapter SHALL send an `update_tool_call` notification with `status: "failed"` and content containing the error message

#### Scenario: Tool call ID tracking
- **WHEN** `AgentSession` fires `on_tool_call` for the first time in a session
- **THEN** the adapter SHALL assign tool call ID `"call_1"`
- **WHEN** a second tool call fires in the same session
- **THEN** the adapter SHALL assign tool call ID `"call_2"`
- **AND** each `update_tool_call` SHALL reference the corresponding tool call ID from the preceding `start_tool_call`

### Requirement: Tool name to ToolKind mapping
The adapter SHALL map codepi tool names to ACP `ToolKind` values. The mapping SHALL be:

| Tool Name | ToolKind |
|-----------|----------|
| `read` | `read` |
| `write` | `edit` |
| `edit` | `edit` |
| `bash` | `execute` |
| `find` | `search` |
| `grep` | `search` |
| `ls` | `read` |
| `lsp_diagnostics` | `read` |
| `lsp_goto_definition` | `read` |
| `lsp_find_references` | `search` |
| `lsp_hover` | `read` |
| `lsp_rename` | `edit` |
| (any other) | `other` |

#### Scenario: Known tool mapped to correct kind
- **WHEN** tool call for `"edit"` fires
- **THEN** the `start_tool_call` notification SHALL have `kind: "edit"`

#### Scenario: Unknown tool mapped to other
- **WHEN** tool call for `"custom_tool"` fires
- **THEN** the `start_tool_call` notification SHALL have `kind: "other"`

### Requirement: Error callback mapped to agent_message_chunk
The system SHALL wire `AgentSession.on_error` to send `agent_message_chunk` notifications with the error message prefixed by `"Error: "`.

#### Scenario: Error during prompt turn
- **WHEN** `AgentSession` fires `on_error("Rate limited")` during a turn
- **THEN** the adapter SHALL send a `session/update` notification with `agent_message_chunk` containing `{"type": "text", "text": "Error: Rate limited"}`

### Requirement: Prompt execution via run_prompt
The adapter SHALL provide a `run_prompt(prompt_blocks)` method that extracts text from ACP content blocks, calls `AgentSession.prompt()`, and returns a `PromptResponse` with the correct `stop_reason`.

#### Scenario: Successful prompt turn
- **WHEN** `run_prompt` is called with `[{"type": "text", "text": "What does main.py do?"}]`
- **THEN** the adapter SHALL extract `"What does main.py do?"` from the content blocks
- **AND** call `AgentSession.prompt("What does main.py do?")`
- **AND** return `PromptResponse(stop_reason="end_turn")` when the turn completes normally

#### Scenario: Prompt with cancellation
- **WHEN** `cancel()` is called during an in-flight `run_prompt()`
- **AND** the `AgentSession` detects cancellation (via `is_cancelled` flag)
- **THEN** `run_prompt` SHALL return `PromptResponse(stop_reason="cancelled")`

#### Scenario: Prompt with exception
- **WHEN** `AgentSession.prompt()` raises an exception (other than `CancelledError`)
- **THEN** `run_prompt` SHALL log the error
- **AND** return `PromptResponse(stop_reason="refusal")`

#### Scenario: Prompt with resource content blocks
- **WHEN** `run_prompt` is called with `[{"type": "resource", "resource": {"uri": "file:///tmp/main.py", "text": "print('hello')"}}]`
- **THEN** the adapter SHALL extract the text from the resource block
- **AND** join all extracted text parts with newlines before passing to `AgentSession.prompt()`

### Requirement: Cancellation via cancel method
The adapter SHALL provide a `cancel()` method that sets the adapter's cancellation flag and calls `AgentSession.cancel()` if the session is initialized.

#### Scenario: Cancel during active turn
- **WHEN** `cancel()` is called while `run_prompt()` is in progress
- **THEN** the adapter SHALL set its internal cancellation flag
- **AND** call `AgentSession.cancel()` to signal the turn to stop

#### Scenario: Cancel with no active session
- **WHEN** `cancel()` is called before any prompt has been sent
- **THEN** the adapter SHALL set its internal cancellation flag without error

### Requirement: File location extraction for tool calls
The adapter SHALL extract file paths from tool call arguments and include them as `locations` in the `start_tool_call` notification.

#### Scenario: Tool with file_path argument
- **WHEN** `on_tool_call("edit", {"file_path": "/tmp/main.py", "old_string": "...", "new_string": "..."})` fires
- **THEN** the `start_tool_call` notification SHALL include `locations: [{"path": "/tmp/main.py"}]`

#### Scenario: Tool with path argument
- **WHEN** `on_tool_call("read", {"path": "/tmp/config.toml"})` fires
- **THEN** the `start_tool_call` notification SHALL include `locations: [{"path": "/tmp/config.toml"}]`

#### Scenario: Tool with no file path
- **WHEN** `on_tool_call("bash", {"command": "ls"})` fires
- **THEN** the `start_tool_call` notification SHALL NOT include `locations` (or it SHALL be empty)

### Requirement: AgentSession cancellation support
`AgentSession` SHALL gain a `cancel()` method that sets an internal `_cancelled` flag, and an `is_cancelled` property that returns the flag's value. The `_cancelled` flag SHALL be reset to `False` at the start of each `prompt()` call.

#### Scenario: Cancel flag set
- **WHEN** `agent_session.cancel()` is called
- **THEN** `agent_session.is_cancelled` SHALL return `True`

#### Scenario: Cancel flag reset on new prompt
- **WHEN** `agent_session.prompt("hello")` is called after a previous cancellation
- **THEN** `agent_session.is_cancelled` SHALL return `False` at the start of the prompt
