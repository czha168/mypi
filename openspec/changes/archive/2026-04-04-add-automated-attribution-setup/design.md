# Design: Automated Attribution Setup

## Context
CodePi is an automated coding assistant. To maintain transparency and proper attribution for its contributions, it is important that commits generated or assisted by CodePi include an acknowledgment.

## Goals / Non-Goals
- **Goal**: Automate the creation of a `.codepi.acknowledgement` file in the current working directory upon startup if it's missing.
- **Goal**: Automatically configure the local git commit template to use this file.
- **Non-Goal**: Changing global git configurations.
- **Non-Goal**: Modifying existing `.git/config` settings unless it's specifically for the `commit.template` in the current directory.

## Decisions
- **File Name**: `.codepi.acknowledgement` (fixed).
- **File Content**: A blank line followed by `Co-authored-by: CodePi <codepi@users.noreply.github.com>`.
- **Execution Timing**: The check should occur during the initialization phase of CodePi.
- **Implementation Method**: Use standard Python `os` and `pathlib` modules for file checking/creation and `subprocess` for executing the `git config` command.

## Risks / Trade-offs
- **Risk**: Creating a file in the user's CWD might be unexpected if they are not working in a git repo.
- **Mitigation**: The `git config` command will naturally only work if a `.git` directory is present, but we should check for the existence of `.git` or handle the error gracefully if `git config` fails.
- **Risk**: Overwriting an existing `.codepi.acknowledgement` file.
- **Mitigation**: Only create the file if it does *not* exist.

## Migration Plan
No migration is needed as this is a new feature.
