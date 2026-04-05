# Proposal: Automated Attribution Setup

## Why
To ensure that all commits made using CodePi include the appropriate attribution in the commit message template. This promotes visibility for CodePi's contributions and maintains a consistent record of automated edits.

## What Changes
- Implement a startup check in CodePi to ensure a `.codepi.acknowledgement` file exists.
- Automatically create the `.codepi.acknowledments` file with standard attribution if it is missing.
- Configure the local Git commit template to use this file.

## Capabilities
- `attribution-setup`: Automated discovery and configuration of the attribution template.

## Impact
- **Files**: `.codepi.acknowledgement` (new file in CWD), `.git/config` (local change).
- **Workflow**: Every time CodePi is initialized/started in a new directory, it will ensure the template is set up.
