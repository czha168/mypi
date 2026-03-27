## ADDED Requirements

### Requirement: Plan mode blocks edits until approved
The system SHALL prevent file modifications when plan mode is active, only allowing the plan file to be edited.

#### Scenario: Edit blocked during planning
- **WHEN** plan mode is active and agent attempts to edit a file (not the plan file)
- **THEN** the edit SHALL be blocked with "Plan mode active - edits not allowed"

#### Scenario: Plan file editable during planning
- **WHEN** plan mode is active and agent edits the designated plan file
- **THEN** the edit SHALL be allowed

### Requirement: Plan mode follows 5-phase workflow
The system SHALL enforce a 5-phase planning workflow: UNDERSTAND → DESIGN → REVIEW → FINALIZE → EXIT.

#### Scenario: Phase progression
- **WHEN** a phase completes its objectives
- **THEN** system SHALL advance to the next phase

#### Scenario: Phase 1 uses explore subagent
- **WHEN** in UNDERSTAND phase
- **THEN** system SHALL use explore subagent for codebase exploration

#### Scenario: Phase 2 uses plan subagent
- **WHEN** in DESIGN phase
- **THEN** system SHALL use plan subagent for architecture design

### Requirement: Plan mode requires user approval
The system SHALL require user approval before exiting plan mode and allowing implementation.

#### Scenario: Exit requires approval
- **WHEN** plan mode reaches EXIT phase
- **THEN** system SHALL prompt user for approval before returning to normal mode

#### Scenario: User can reject plan
- **WHEN** user rejects the plan
- **THEN** system SHALL return to DESIGN phase for revisions

### Requirement: Plan mode preserves context across phases
The system SHALL preserve exploration results and design decisions across plan mode phases.

#### Scenario: Design has access to exploration
- **WHEN** entering DESIGN phase
- **THEN** results from UNDERSTAND phase SHALL be available

#### Scenario: Review shows full plan
- **WHEN** entering REVIEW phase
- **THEN** complete plan with all sections SHALL be presented

### Requirement: Plan mode can be exited early
The system SHALL allow users to exit plan mode early if needed.

#### Scenario: User cancels plan mode
- **WHEN** user sends cancel signal (Escape key or cancel command)
- **THEN** system SHALL exit plan mode and discard the plan

### Requirement: Plan file location is configurable
The system SHALL allow specifying the plan file location or use a default.

#### Scenario: Default plan location
- **WHEN** no plan file location is specified
- **THEN** system SHALL use `.codepi/plans/plan-<timestamp>.md` as default

#### Scenario: Custom plan location
- **WHEN** user specifies a plan file location
- **THEN** system SHALL use that location for the plan file
