## ADDED Requirements

### Requirement: Go to Definition Tool

The system SHALL provide an `lsp_goto_definition` tool that navigates to the definition of a symbol at a given position in a Python file.

#### Scenario: Navigate to function definition
- **WHEN** the tool is called with path="src/utils.py", line=10, character=5 where a function call exists
- **THEN** the system returns the file path, line, and character where the function is defined

#### Scenario: Navigate to class definition
- **WHEN** the tool is called on a class instantiation
- **THEN** the system returns the location of the class definition

#### Scenario: No definition found
- **WHEN** the tool is called on a symbol with no definition (e.g., built-in)
- **THEN** the system returns an empty result list with no error

#### Scenario: Multiple definitions
- **WHEN** a symbol has multiple definitions (e.g., in different files)
- **THEN** the system returns all definition locations

---

### Requirement: Find References Tool

The system SHALL provide an `lsp_find_references` tool that finds all references to a symbol at a given position in a Python file.

#### Scenario: Find all function usages
- **WHEN** the tool is called on a function definition
- **THEN** the system returns all locations where the function is called or referenced

#### Scenario: Find class usages
- **WHEN** the tool is called on a class definition
- **THEN** the system returns all instantiation sites and inheritance references

#### Scenario: Include declaration
- **WHEN** the tool is called with include_declaration=true
- **THEN** the system includes the symbol's own definition in the results

#### Scenario: Exclude declaration
- **WHEN** the tool is called with include_declaration=false
- **THEN** the system excludes the symbol's own definition from results

---

### Requirement: Diagnostics Tool

The system SHALL provide an `lsp_diagnostics` tool that retrieves diagnostics (errors, warnings, hints) for Python files.

#### Scenario: Get diagnostics for a file
- **WHEN** the tool is called with path="src/main.py"
- **THEN** the system returns all diagnostics for that file with severity, message, line, and character

#### Scenario: Get diagnostics for directory
- **WHEN** the tool is called with path="src/" and extension=".py"
- **THEN** the system returns diagnostics for all Python files in the directory

#### Scenario: Filter by severity
- **WHEN** the tool is called with severity="error"
- **THEN** the system returns only error-level diagnostics (no warnings or hints)

#### Scenario: No diagnostics
- **WHEN** the tool is called on a file with no issues
- **THEN** the system returns an empty list

---

### Requirement: Rename Symbol Tool

The system SHALL provide an `lsp_rename` tool that renames a symbol across all references in the workspace.

#### Scenario: Rename local variable
- **WHEN** the tool is called with path="src/main.py", line=5, character=10, new_name="new_var"
- **THEN** the system renames the symbol and returns a preview of all changes (files and line ranges)

#### Scenario: Rename function
- **WHEN** the tool is called on a function definition
- **THEN** the system shows all call sites that will be updated

#### Scenario: Dry run mode
- **WHEN** the tool is called with dry_run=true
- **THEN** the system returns the changes that would be made without modifying files

#### Scenario: Apply changes
- **WHEN** the tool is called with dry_run=false
- **THEN** the system applies all file edits and confirms completion

---

### Requirement: Hover Information Tool

The system SHALL provide an `lsp_hover` tool that retrieves type information and documentation for a symbol at a given position.

#### Scenario: Get type info for variable
- **WHEN** the tool is called on a variable
- **THEN** the system returns the inferred type and any inline documentation

#### Scenario: Get function signature
- **WHEN** the tool is called on a function
- **THEN** the system returns the full signature with parameter types and return type

#### Scenario: Get docstring
- **WHEN** the tool is called on a symbol with a docstring
- **THEN** the system includes the docstring content in the response

#### Scenario: No hover info available
- **WHEN** the tool is called on a position with no symbol
- **THEN** the system returns an empty response with no error

---

### Requirement: LSP Server Management

The system SHALL automatically manage the LSP server lifecycle.

#### Scenario: Auto-start on first use
- **WHEN** any LSP tool is called for the first time
- **THEN** the system starts the configured LSP server if not already running

#### Scenario: Server detection
- **WHEN** no LSP server is specified in config
- **THEN** the system auto-detects available servers in order: pyright, pylsp, jedi-language-server

#### Scenario: No server available
- **WHEN** no LSP server is found on PATH
- **THEN** the system returns a helpful error message with installation instructions

#### Scenario: Server crash recovery
- **WHEN** the LSP server crashes during operation
- **THEN** the system detects the failure and restarts the server on the next tool call
