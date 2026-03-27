### Requirement: Assistant response panel starts on new line
The RichRenderer SHALL ensure that the assistant response Panel in `end_turn()` always starts on a fresh line, regardless of how streaming tokens ended.

#### Scenario: Panel starts on new line after streaming without trailing newline
- **WHEN** streaming tokens are printed without a trailing newline character
- **AND** `end_turn()` is called to display the assistant Panel
- **THEN** the Panel SHALL start on a new line, not continuing from the streaming output

#### Scenario: Panel starts on new line after streaming with trailing newline
- **WHEN** streaming tokens end with a newline character
- **AND** `end_turn()` is called to display the assistant Panel
- **THEN** the Panel SHALL still start on a new line with at most one blank line gap

#### Scenario: Empty buffer does not print Panel
- **WHEN** the buffer in `end_turn()` is empty or contains only whitespace
- **THEN** no Panel SHALL be printed (existing behavior preserved)
