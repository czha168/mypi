## ADDED Requirements

### Requirement: LSP tool files SHALL have no Pyright errors
All files under `codepi/tools/lsp/` SHALL pass Pyright type checking with zero errors. This includes proper handling of third-party `lsp_client` library attributes that lack type stubs.

#### Scenario: LSP client attribute access is type-safe
- **WHEN** Pyright analyzes `codepi/tools/lsp/` directory
- **THEN** zero errors are reported for attribute access on `lsp_client.Client` instances

#### Scenario: MypiLSPClient implements all abstract methods
- **WHEN** Pyright analyzes the `MypiLSPClient` class in `client.py`
- **THEN** `get_language_config`, `check_server_compatibility`, and `create_default_servers` are properly implemented with correct signatures

### Requirement: LSP init SHALL resolve forward references
The `make_lsp_tool_registry` function in `codepi/tools/lsp/__init__.py` SHALL import `ToolRegistry` at the module level or use a proper forward reference, not an unresolved string literal.

#### Scenario: ToolRegistry is properly imported
- **WHEN** Pyright analyzes `codepi/tools/lsp/__init__.py`
- **THEN** the `ToolRegistry` type is resolved without error

### Requirement: Rename tool SHALL handle all code paths
The `execute` method in `codepi/tools/lsp/rename.py` SHALL ensure `lines` is always bound before use, even in multi-line edit paths.

#### Scenario: Lines variable is bound for multi-line edits
- **WHEN** a rename involves multi-line edits (`start_line != end_line`)
- **THEN** the `lines` variable is defined and accessible at line 96
