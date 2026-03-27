## ADDED Requirements

### Requirement: Security monitor evaluates actions before execution
The security monitor SHALL evaluate tool calls before execution and return ALLOW, BLOCK, or ASK decisions.

#### Scenario: Allow safe action
- **WHEN** action is safe (reading files, searching code)
- **THEN** security monitor SHALL return ALLOW

#### Scenario: Block dangerous action
- **WHEN** action is clearly dangerous (rm -rf, credential exposure)
- **THEN** security monitor SHALL return BLOCK with reason

#### Scenario: Ask for ambiguous action
- **WHEN** action has unclear risk (pushing to shared branch)
- **THEN** security monitor SHALL return ASK with question for user

### Requirement: Security monitor detects destructive operations
The security monitor SHALL detect and block destructive operations.

#### Scenario: rm -rf blocked
- **WHEN** bash command contains "rm -rf"
- **THEN** security monitor SHALL return BLOCK with "Destructive operation detected"

#### Scenario: DROP TABLE blocked
- **WHEN** bash command or code contains "DROP TABLE"
- **THEN** security monitor SHALL return BLOCK with "Database destructive operation detected"

### Requirement: Security monitor detects hard-to-reverse operations
The security monitor SHALL detect operations that are difficult to reverse.

#### Scenario: Force push flagged
- **WHEN** bash command is "git push --force"
- **THEN** security monitor SHALL return ASK with "Force push can overwrite upstream history. Proceed?"

#### Scenario: Hard reset flagged
- **WHEN** bash command contains "git reset --hard"
- **THEN** security monitor SHALL return ASK with "Hard reset will lose uncommitted changes. Proceed?"

### Requirement: Security monitor detects shared state operations
The security monitor SHALL detect operations that affect shared state visible to others.

#### Scenario: Git push flagged
- **WHEN** bash command is "git push"
- **THEN** security monitor SHALL return ASK with "Pushing to remote. Confirm?"

#### Scenario: PR creation flagged
- **WHEN** action creates a pull request
- **THEN** security monitor SHALL return ASK with "Creating PR visible to team. Confirm?"

### Requirement: Security monitor detects credential exposure
The security monitor SHALL detect potential credential or secret exposure.

#### Scenario: .env file read warning
- **WHEN** reading a file named ".env" or containing "credentials"
- **THEN** security monitor SHALL return ASK with "File may contain secrets. Confirm read?"

### Requirement: Security monitor is configurable
The security monitor SHALL be configurable to adjust sensitivity and enable/disable rules.

#### Scenario: Disable specific rule
- **WHEN** config sets `security.rules.force-push = "allow"`
- **THEN** security monitor SHALL NOT flag force push operations

#### Scenario: Disable monitor entirely
- **WHEN** config sets `security.enabled = false`
- **THEN** all actions SHALL be allowed without security checks
