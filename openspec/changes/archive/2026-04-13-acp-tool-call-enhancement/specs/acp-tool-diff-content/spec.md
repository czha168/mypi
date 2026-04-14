## ADDED Requirements

### Requirement: Edit tool results include diff content
When the `edit` tool completes successfully, the `tool_call_update` notification SHALL include a `FileEditToolCallContent` entry (type `diff`) with the file path, old text, and new text from the tool's arguments.

#### Scenario: Edit tool produces diff
- **WHEN** `on_tool_result` fires for tool `edit` with arguments `{"file_path": "/tmp/main.py", "old_string": "old code", "new_string": "new code"}` and the result has no error
- **THEN** the `tool_call_update` notification SHALL include content of type `diff`
- **AND** the diff SHALL have `path: "/tmp/main.py"`, `oldText: "old code"`, `newText: "new code"`

#### Scenario: Edit tool with error produces no diff
- **WHEN** `on_tool_result` fires for tool `edit` and the result has an error (e.g., "old_string not found")
- **THEN** the `tool_call_update` notification SHALL NOT include diff content
- **AND** the notification SHALL contain only the error text content

### Requirement: Write tool results include diff content
When the `write` tool completes successfully, the `tool_call_update` notification SHALL include a `FileEditToolCallContent` entry with the file path and new content. The `oldText` SHALL be `None` (representing a full file replacement).

#### Scenario: Write tool produces diff
- **WHEN** `on_tool_result` fires for tool `write` with arguments `{"file_path": "/tmp/new.py", "content": "print('hello')"}` and the result has no error
- **THEN** the `tool_call_update` notification SHALL include content of type `diff`
- **AND** the diff SHALL have `path: "/tmp/new.py"`, `oldText: None`, `newText: "print('hello')"`

#### Scenario: Write tool with error produces no diff
- **WHEN** `on_tool_result` fires for tool `write` and the result has an error (e.g., "permission denied")
- **THEN** the `tool_call_update` notification SHALL NOT include diff content
- **AND** the notification SHALL contain only the error text content

### Requirement: Non-edit tools produce no diff content
Tool calls for tools other than `edit` and `write` SHALL NOT include diff content in their `tool_call_update` notifications.

#### Scenario: Bash tool produces text content only
- **WHEN** `on_tool_result` fires for tool `bash` with a successful result
- **THEN** the `tool_call_update` notification SHALL include only text content (no diff)
