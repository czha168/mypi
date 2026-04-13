## ADDED Requirements

### Requirement: /websearch is registered as a builtin command
The `InteractiveMode._register_builtin_commands()` method SHALL include `/websearch` in the builtin command list so it appears in auto-completion.

#### Scenario: /websearch appears in completion
- **WHEN** the user types `/w` in the interactive prompt
- **THEN** the auto-completion dropdown SHALL show `/websearch` with its description

#### Scenario: /websearch appears in command list
- **WHEN** `CommandRegistry.list_commands()` is called
- **THEN** the list SHALL include a `Command` with `name="/websearch"`, `description="Search the web using DuckDuckGo"`, and `category="general"`
