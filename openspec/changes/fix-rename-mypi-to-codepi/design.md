# Design: Rename mypi to codepi

## Context
The project is transitioning from the "mypi" brand to "codepi". This requires a thorough update of all user-facing strings and the configuration directory structure.

## Goals / Non-Goals
- **Goals**
  - Update all CLI welcome messages and branding strings.
  - Change the default configuration path to `~/.codepi`.
  - Implement an automatic migration path for existing `~/.mypi` configurations.
- **Non-Goals**
  - Changing the underlying logic of the agent.
  - Deep refactoring of internal variable names (unless they directly impact the path/branding).

## Decisions
- **Migration Strategy**: Use a simple `os.rename` or `shutil.move` for the config directory if `~/.mypi` is detected during startup.
- **String Replacement**: Use a global find-and-replace for known branding strings in the UI layer.

## Risks / Trade-offs
- **Risk**: If migration fails (e.g., permission issues), the user might lose access to their config.
- **Mitigation**: Attempt migration only if `~/.mypi` exists and the new path `~/.codepi` is not already occupied by a different directory.
- **Risk**: Broken scripts/aliases that rely on the `~/.mypi` path.
- **Mitigation**: Documentation update (out of scope for this change).

## Migration Plan
1. Detection of `~/.mypi`.
2. Moving contents to `~/.codepi`.
3. Cleanup of old directory.
