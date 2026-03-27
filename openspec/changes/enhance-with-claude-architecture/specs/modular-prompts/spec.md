## ADDED Requirements

### Requirement: Prompt components are composable
The system SHALL provide a modular prompt architecture where components (persona, tools, constraints, modes) can be combined into a final system prompt.

#### Scenario: Default prompt composition
- **WHEN** no custom components are specified
- **THEN** system SHALL compose a default prompt from base persona, tool descriptions, and standard constraints

#### Scenario: Custom constraint injection
- **WHEN** a mode (e.g., plan mode) is active
- **THEN** system SHALL inject mode-specific constraints into the prompt

### Requirement: Prompt templates support variable interpolation
The system SHALL support YAML-based prompt templates with `{{variable}}` interpolation for dynamic content.

#### Scenario: Tool list interpolation
- **WHEN** rendering a prompt template with `{{tools}}` variable
- **THEN** system SHALL replace it with formatted tool descriptions from the tool registry

#### Scenario: Missing variable handling
- **WHEN** a template references an undefined variable
- **THEN** system SHALL raise a clear error indicating the missing variable name

### Requirement: Prompt components are lazily loaded
The system SHALL load prompt components on demand to minimize memory usage and startup time.

#### Scenario: First access loads component
- **WHEN** a prompt component is accessed for the first time
- **THEN** system SHALL load it from disk and cache it

#### Scenario: Subsequent access uses cache
- **WHEN** a prompt component is accessed again
- **THEN** system SHALL return the cached version without disk I/O

### Requirement: Extension can modify prompt composition
The system SHALL allow extensions to modify the final system prompt via `BeforeAgentStartEvent`.

#### Scenario: Extension adds custom instructions
- **WHEN** an extension modifies `BeforeAgentStartEvent.system_prompt`
- **THEN** the modified prompt SHALL be used for the LLM request

### Requirement: Output efficiency guidelines are included
The system SHALL include output efficiency guidelines in the default prompt composition.

#### Scenario: Efficiency guidelines present
- **WHEN** composing the default system prompt
- **THEN** it SHALL include guidelines for concise, direct output
