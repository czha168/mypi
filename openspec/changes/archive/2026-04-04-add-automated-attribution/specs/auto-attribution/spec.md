## ADDED Requirements

The system SHALL create a `.codepi.acknowledgement` file in the current working directory when CodePi
starts, if the file does **not** already exist.

The created file SHALL contain:
- An initial blank line.
- The string `Co-authored-by: CodePi <codepi@users.noreply.github.com>` on the following line.

The system SHALL then execute the shell command:
```
git config --local commit.template .codepi.acknowledgement
```

#### Scenario
WHEN CodePi starts and `.codepi.acknowledgement` does **not** exist, THEN the system creates the file
with the specified content and runs the Git configuration command.
