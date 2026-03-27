## ADDED Requirements

### Requirement: Explore subagent is strictly read-only
The explore subagent SHALL operate in read-only mode, prohibited from any file modifications.

#### Scenario: Write tool is unavailable
- **WHEN** explore subagent attempts to use the write tool
- **THEN** the tool call SHALL fail with "Tool not available in read-only mode"

#### Scenario: Edit tool is unavailable
- **WHEN** explore subagent attempts to use the edit tool
- **THEN** the tool call SHALL fail with "Tool not available in read-only mode"

#### Scenario: Bash commands are filtered
- **WHEN** explore subagent uses bash tool with a modifying command (mkdir, rm, cp, mv, git add, git commit)
- **THEN** the command SHALL be rejected with "Only read-only operations allowed"

### Requirement: Explore subagent has focused tool set
The explore subagent SHALL only have access to: read, find, grep, ls, and read-only bash operations.

#### Scenario: Tool whitelist enforced
- **WHEN** explore subagent session is created
- **THEN** only whitelisted tools SHALL be registered

### Requirement: Explore subagent returns structured results
The explore subagent SHALL return results in a structured format with file paths, relevant excerpts, and summary.

#### Scenario: Search returns absolute paths
- **WHEN** explore subagent completes a search task
- **THEN** all file paths in the result SHALL be absolute paths

#### Scenario: Results include context
- **WHEN** explore subagent finds matches
- **THEN** results SHALL include surrounding context lines when relevant

### Requirement: Explore subagent is efficient
The explore subagent SHALL optimize for fast response time by parallelizing tool calls where possible.

#### Scenario: Parallel file reads
- **WHEN** explore subagent needs to read multiple files
- **THEN** it SHALL issue parallel read requests rather than sequential

### Requirement: Explore subagent prompt emphasizes speed
The explore subagent system prompt SHALL include instructions to return quickly and efficiently.

#### Scenario: Prompt contains efficiency directive
- **WHEN** explore subagent system prompt is composed
- **THEN** it SHALL include "You are meant to be a fast agent that returns output as quickly as possible"
