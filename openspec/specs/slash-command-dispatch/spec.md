## ADDED Requirements

### Requirement: Slash command dispatch intercepts input before LLM
The `InteractiveMode` SHALL intercept user input starting with `/` and attempt to dispatch it to a registered command handler before forwarding it to `AgentSession.prompt()`. If the command is recognized and handled locally, the input SHALL NOT be sent to the LLM.

#### Scenario: Known command is intercepted
- **WHEN** the user types `/exit` in interactive mode
- **THEN** the system SHALL handle the command locally and SHALL NOT call `AgentSession.prompt()` with `/exit`

#### Scenario: Unknown command passes through
- **WHEN** the user types `/unknown-command` and no handler is registered for it
- **THEN** the system SHALL pass the input through to `AgentSession.prompt()` unchanged

#### Scenario: Non-slash input is not intercepted
- **WHEN** the user types `help me with this code` (no leading `/`)
- **THEN** the system SHALL pass the input directly to `AgentSession.prompt()` without attempting dispatch

### Requirement: /exit command terminates the session
The `/exit` command SHALL terminate the interactive session by stopping the main loop. The `/quit` alias SHALL behave identically.

#### Scenario: /exit stops the session
- **WHEN** the user types `/exit`
- **THEN** the system SHALL set the running flag to `False`, break the main loop, and display a goodbye message

#### Scenario: /quit alias works
- **WHEN** the user types `/quit`
- **THEN** the system SHALL behave identically to `/exit`

#### Scenario: /exit with trailing whitespace
- **WHEN** the user types `/exit  ` (with trailing spaces)
- **THEN** the system SHALL still terminate the session (whitespace is ignored)

### Requirement: /websearch command executes search directly
The `/websearch` command SHALL accept a search query as its argument, execute the search using `WebSearchTool`, and render the results in the terminal via `RichRenderer`. The LLM SHALL NOT be involved in the search.

#### Scenario: Basic web search
- **WHEN** the user types `/websearch Python asyncio tutorial`
- **THEN** the system SHALL call `WebSearchTool.execute(query="Python asyncio tutorial")` and render the results in the terminal

#### Scenario: Web search with no arguments
- **WHEN** the user types `/websearch` with no arguments
- **THEN** the system SHALL display a usage message indicating the command requires a query (e.g., "Usage: /websearch <query>")

#### Scenario: Web search when ddgs not installed
- **WHEN** the user types `/websearch test query` and the `ddgs` package is not installed
- **THEN** the system SHALL display an error message with installation instructions

#### Scenario: Web search results are displayed locally
- **WHEN** `/websearch` returns results
- **THEN** the results SHALL be rendered via `RichRenderer.render_info()` and SHALL NOT be sent to the LLM

### Requirement: /help command displays all registered commands
The `/help` command SHALL display a formatted list of all registered commands with their names, aliases, and descriptions.

#### Scenario: Help shows all commands
- **WHEN** the user types `/help`
- **THEN** the system SHALL display all commands from `CommandRegistry.list_commands()` including name, aliases, and description

#### Scenario: Help includes /websearch
- **WHEN** `/websearch` is registered as a builtin command
- **AND** the user types `/help`
- **THEN** the displayed list SHALL include `/websearch` with its description

### Requirement: Command dispatch preserves opsx command handling
The `/opsx:*` commands SHALL continue to be handled by `AgentSession._handle_opsx_command()` as before. The dispatch layer SHALL pass unrecognized `/opsx:*` input through to `AgentSession.prompt()`.

#### Scenario: opsx command passes through
- **WHEN** the user types `/opsx:explore some topic`
- **THEN** the dispatch layer SHALL NOT handle it locally and SHALL pass it to `AgentSession.prompt()` where `_handle_opsx_command` processes it
