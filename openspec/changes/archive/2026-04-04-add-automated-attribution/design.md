## Context
CodePi is a local development tool that augments the Git workflow by running scripts on repository
startup.  The new capability focuses on automating the addition of an attribution line to every
commit.

### Constraints
- The process must be idempotent – running CodePi multiple times should not overwrite an existing
  file or change Git configuration repeatedly.
- Only local Git configuration may be modified; global or system configurations must remain
  untouched.
- The solution must be available on all platforms where CodePi runs (Linux, macOS, Windows).

### Stakeholders
- Individual developers using CodePi.
- Projects that require attribution in commit messages.

## Goals / Non‑Goals
- **Goal:** Automatically add a standard co‑authored by line to new commits.
- **Non‑Goal:** Alter commit contents beyond adding the attribution line.

## Design Decisions
1. **File creation logic:** Use a simple file existence check (`os.path.exists`) before creating the
   file to ensure idempotence.
2. **Content formatting:** Write a newline first, then the attribution line, to match typical Git
   commit template styles.
3. **Git configuration:** Execute `git config --local commit.template` using a subprocess call.  This
   will be wrapped in a try‑except to handle environments where Git is not present.
4. **Platform support:** The implementation uses Python’s `subprocess.run` with `shell=True` and
   normalizes the command string for each platform.

## Risks / Trade‑offs
- **Risk:** The repository might already have a different `.git` commit template.  Overwriting it
  could break existing workflows.  **Mitigation:** We only set the template if the file does
  not already exist.
- **Risk:** A missing Git binary will cause the command to fail.  **Mitigation:** Detect the
  failure and log a warning instead of raising an exception.

## Migration Plan
1. CodePi will run the file‑creation logic during the startup sequence.
2. In case of conflicting existing templates, developers will be notified and have the option to
   use a custom template.
3. Rollback is trivial: simply delete the `.codepi.acknowledgement` file and remove the local
   Git config entry (`git config --unset commit.template`).
