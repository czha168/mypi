# Specification: config-migration

## MODIFIED Requirements
- The default configuration file path MUST be located at `~/.codepi` instead of `~/.mypi`.

#### Scenario: Config Path Update
- **WHEN** the application looks for its configuration
- **THEN** it looks in `~/.codepi`

## ADDED Requirements
- The system SHOULD check for the existence of `~/.mypi` and migrate its contents to `~/.codepi` if found, to ensure continuity for existing users.

#### Scenario: Migration of existing config
- **WHEN** a `~/.mypi` directory exists
- **THEN** the contents are moved to `~/.codepi` and `~/.mypi` is removed.
