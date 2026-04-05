# Proposal: Rename mypi to codepi

## Why
The project is rebranding from "mypi" to "codepi". To maintain brand consistency, all references to "mypi" in user-facing messages and configuration paths must be updated to "codepi".

## What Changes
- Update welcome message in the CLI/agent output.
- Update the default configuration file path from `~/.mypi` to `~/.codepi`.

## Capabilities
- `branding-update`: Update all text strings and identifiers from "mypi" to "codepi".
- `config-migration`: Update the configuration file directory and path.

## Impact
- CLI output behavior.
- User's local configuration storage.
- Existing configuration files in `~/.mypi` will be orphaned (migration strategy needed).
