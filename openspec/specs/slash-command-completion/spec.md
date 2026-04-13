## ADDED Requirements

### Requirement: Command registry defines all slash commands
The system SHALL maintain a `CommandRegistry` class that holds all registered slash commands. Each command SHALL have a name (starting with `/`), a human-readable description, an optional list of aliases, and a category. The registry SHALL support dynamic registration of commands at runtime.

#### Scenario: Register a new slash command
- **WHEN** `CommandRegistry.register(name="/help", description="Show help", category="general")` is called
- **THEN** the command `/help` SHALL be available in the registry with the given metadata

#### Scenario: Register a command with aliases
- **WHEN** `CommandRegistry.register(name="/opsx:explore", description="Explore mode", aliases=["/explore"])` is called
- **THEN** both `/opsx:explore` and `/explore` SHALL resolve to the same command entry

#### Scenario: Duplicate registration overwrites
- **WHEN** a command with the same name is registered twice
- **THEN** the second registration SHALL overwrite the first without error

### Requirement: Command registry loads commands from SkillLoader
The `CommandRegistry` SHALL provide a `load_from_skill_loader(skill_loader)` method that scans loaded skills and registers `/opsx:<name>` commands for each skill with a matching naming convention.

#### Scenario: Skills loaded as opsx commands
- **WHEN** `load_from_skill_loader` is called with a `SkillLoader` containing skills named `opsx-explore`, `opsx-apply`, and `opsx-archive-change`
- **THEN** the registry SHALL contain commands `/opsx:explore`, `/opsx:apply`, and `/opsx:archive-change` with descriptions from the skill metadata

#### Scenario: Skill without opsx prefix is skipped
- **WHEN** a skill named `my-custom-skill` (no `opsx-` prefix) exists in the loader
- **THEN** it SHALL NOT be registered as a slash command

### Requirement: Auto-completion triggers on `/` character
When the user types `/` as the first character in the interactive input prompt, the system SHALL display a completion dropdown listing all registered slash commands that match the current prefix.

#### Scenario: Typing `/` shows all commands
- **WHEN** the user types `/` as the first character of input
- **THEN** a completion dropdown SHALL appear showing all registered slash commands with their descriptions

#### Scenario: Typing `/h` filters to matching commands
- **WHEN** the user types `/h`
- **THEN** the dropdown SHALL show only commands starting with `/h` (e.g., `/help`)

#### Scenario: Typing `/opsx:` filters to opsx commands
- **WHEN** the user types `/opsx:`
- **THEN** the dropdown SHALL show only commands starting with `/opsx:` (e.g., `/opsx:explore`, `/opsx:apply`, `/opsx:archive-change`)

#### Scenario: No match shows empty dropdown
- **WHEN** the user types `/xyz`
- **AND** no commands match the prefix `/xyz`
- **THEN** the dropdown SHALL show no suggestions

### Requirement: Completion inserts command text
When the user selects a completion suggestion, the system SHALL insert the full command text into the input buffer, replacing the typed prefix.

#### Scenario: Selecting a completion
- **WHEN** the user types `/op` and selects `/opsx:explore` from the dropdown
- **THEN** the input buffer SHALL contain `/opsx:explore` with the cursor positioned after the inserted text

#### Scenario: Tab completion selects first match
- **WHEN** the user types `/op` and presses Tab
- **AND** there is exactly one matching command
- **THEN** the input buffer SHALL be filled with that command's full name

### Requirement: Completion does not trigger for non-slash input
The completion dropdown SHALL NOT appear when the user's input does not start with `/`.

#### Scenario: Regular text input
- **WHEN** the user types `help me fix this bug`
- **THEN** no completion dropdown SHALL appear

#### Scenario: Slash not at start
- **WHEN** the user types `use the /help command`
- **THEN** no completion dropdown SHALL appear (completion only triggers when `/` is the first character)

### Requirement: RichInput uses prompt_toolkit with completer
The `RichInput` class SHALL use `prompt_toolkit.PromptSession` internally with a `SlashCommandCompleter` attached, replacing the current `console.input()` implementation.

#### Scenario: RichInput initialization with completer
- **WHEN** `RichInput(command_registry=registry)` is constructed
- **THEN** the internal `PromptSession` SHALL have `completer=SlashCommandCompleter(registry)` and `complete_while_typing=True`

#### Scenario: Public API preserved
- **WHEN** `await rich_input.get_user_input()` is called
- **THEN** it SHALL return the user's input string, maintaining the same return type and behavior as before

### Requirement: /websearch is registered as a builtin command
The `InteractiveMode._register_builtin_commands()` method SHALL include `/websearch` in the builtin command list so it appears in auto-completion.

#### Scenario: /websearch appears in completion
- **WHEN** the user types `/w` in the interactive prompt
- **THEN** the auto-completion dropdown SHALL show `/websearch` with its description

#### Scenario: /websearch appears in command list
- **WHEN** `CommandRegistry.list_commands()` is called
- **THEN** the list SHALL include a `Command` with `name="/websearch"`, `description="Search the web using DuckDuckGo"`, and `category="general"`
