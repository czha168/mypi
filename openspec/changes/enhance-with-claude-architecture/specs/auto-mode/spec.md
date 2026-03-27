## ADDED Requirements

### Requirement: Auto mode enables continuous execution
The system SHALL support auto mode where the agent executes continuously with minimal user interruption.

#### Scenario: Auto mode flag
- **WHEN** auto mode is enabled via CLI flag `--auto` or command
- **THEN** agent SHALL proceed autonomously through multi-step tasks

#### Scenario: Auto mode makes reasonable assumptions
- **WHEN** encountering ambiguity in auto mode
- **THEN** agent SHALL make reasonable default choices rather than asking

### Requirement: Auto mode minimizes interruptions
The system SHALL minimize user interruptions in auto mode, only asking when genuinely necessary.

#### Scenario: Skip clarifying questions
- **WHEN** auto mode is active and task could proceed with reasonable assumption
- **THEN** agent SHALL NOT ask clarifying questions

#### Scenario: Ask for fundamental choices
- **WHEN** auto mode encounters fundamentally different approaches with no clear default
- **THEN** agent SHALL ask user for direction

### Requirement: Auto mode prefers action over planning
The system SHALL inject prompts encouraging immediate action over extended planning in auto mode.

#### Scenario: Skip plan mode
- **WHEN** auto mode is active and user has not explicitly requested planning
- **THEN** agent SHALL start implementing directly

### Requirement: Auto mode has iteration limits
The system SHALL enforce maximum iteration limits to prevent runaway execution.

#### Scenario: Iteration limit reached
- **WHEN** auto mode reaches max iterations (default: 100)
- **THEN** agent SHALL pause and prompt user for continuation

#### Scenario: Iteration limit configurable
- **WHEN** config specifies `auto.max_iterations`
- **THEN** system SHALL use that limit instead of default

### Requirement: Auto mode requires approval for sensitive operations
The system SHALL require user approval for configured sensitive operations even in auto mode.

#### Scenario: Push requires approval
- **WHEN** auto mode is active and agent wants to run `git push`
- **THEN** system SHALL prompt user for approval if push is in `auto.require_approval_for`

#### Scenario: PR requires approval
- **WHEN** auto mode is active and agent wants to create a PR
- **THEN** system SHALL prompt user for approval if pr is in `auto.require_approval_for`

### Requirement: Auto mode never posts to public services
The system SHALL prevent posting to public services in auto mode without explicit approval.

#### Scenario: Public gist blocked
- **WHEN** auto mode attempts to post to public GitHub gist
- **THEN** system SHALL block the action and require explicit approval

### Requirement: Auto mode is thorough
The system SHALL complete full tasks including tests, linting, and verification in auto mode.

#### Scenario: Tests run after implementation
- **WHEN** auto mode completes implementation
- **THEN** agent SHALL run tests to verify changes

#### Scenario: Lint after edits
- **WHEN** auto mode makes code changes
- **THEN** agent SHALL run linting/type checking
