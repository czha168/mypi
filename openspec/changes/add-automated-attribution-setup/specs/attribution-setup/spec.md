## ADDED Requirements

The system MUST ensure the presence of a local attribution template file before proceeding with operations.

### Scenario: Missing attribution file
**WHEN** CodePi starts in a directory where `.codepi.acknowledgement` does not exist
**THEN** it SHALL create the file with the content:
```

Co-authored-by: CodePi <codepi@users.noreply.github.com>
```

### Scenario: Setting git commit template
**WHEN** the `.codepi.acknowledgement` file is created or verified
**THEN** the system SHALL execute `git config --local commit.template .codepi.acknowledgement` to ensure the local repository uses this template for commits.
