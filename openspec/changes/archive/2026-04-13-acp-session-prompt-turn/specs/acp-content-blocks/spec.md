## ADDED Requirements

### Requirement: Text content block builder
The system SHALL provide a `text_content(text)` function that returns a dict `{"type": "text", "text": text}` compatible with ACP `ContentBlock` format.

#### Scenario: Building text content block
- **WHEN** `text_content("Hello world")` is called
- **THEN** it SHALL return `{"type": "text", "text": "Hello world"}`

### Requirement: Resource content block builder
The system SHALL provide a `resource_content(uri, text, mime_type=None)` function that returns a dict with `type: "resource"` and a nested `resource` dict containing `uri`, `text`, and optionally `mimeType`.

#### Scenario: Resource block without MIME type
- **WHEN** `resource_content("file:///tmp/main.py", "print('hello')")` is called
- **THEN** it SHALL return `{"type": "resource", "resource": {"uri": "file:///tmp/main.py", "text": "print('hello')"}}`

#### Scenario: Resource block with MIME type
- **WHEN** `resource_content("file:///tmp/main.py", "print('hello')", mime_type="text/x-python")` is called
- **THEN** it SHALL return `{"type": "resource", "resource": {"uri": "file:///tmp/main.py", "text": "print('hello')", "mimeType": "text/x-python"}}`

### Requirement: Diff content block builder
The system SHALL provide a `diff_content(path, old_text, new_text)` function that returns a dict with `type: "diff"`, `path`, `oldText` (nullable), and `newText`.

#### Scenario: Diff block with old and new text
- **WHEN** `diff_content("/tmp/main.py", "old code", "new code")` is called
- **THEN** it SHALL return `{"type": "diff", "path": "/tmp/main.py", "oldText": "old code", "newText": "new code"}`

#### Scenario: Diff block with None old text (new file)
- **WHEN** `diff_content("/tmp/new.py", None, "new file content")` is called
- **THEN** it SHALL return `{"type": "diff", "path": "/tmp/new.py", "newText": "new file content"}`
- **AND** `oldText` SHALL NOT be present in the dict

### Requirement: Terminal content block builder
The system SHALL provide a `terminal_content(terminal_id)` function that returns a dict `{"type": "terminal", "terminalId": terminal_id}`.

#### Scenario: Terminal content block
- **WHEN** `terminal_content("term_1")` is called
- **THEN** it SHALL return `{"type": "terminal", "terminalId": "term_1"}`
