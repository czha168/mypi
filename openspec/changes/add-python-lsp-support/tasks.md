## 1. Setup & Dependencies

- [x] 1.1 Add `lsp-client` dependency to pyproject.toml
- [x] 1.2 Create `mypi/tools/lsp/` module directory structure
- [x] 1.3 Add LSP configuration section to `mypi/config.py` (server selection, workspace path)

## 2. LSP Client Infrastructure

- [x] 2.1 Create `mypi/tools/lsp/client.py` with `LSPClientManager` singleton class
- [x] 2.2 Implement server auto-detection logic (pyright → pylsp → jedi-language-server)
- [x] 2.3 Implement server startup with workspace initialization
- [x] 2.4 Implement graceful shutdown and cleanup
- [x] 2.5 Add server crash detection and auto-restart logic
- [x] 2.6 Create helpful error message for missing LSP server

## 3. LSP Tool Implementations

- [x] 3.1 Create `mypi/tools/lsp/base.py` with shared LSP tool base class
- [x] 3.2 Implement `lsp_goto_definition` tool in `mypi/tools/lsp/goto_definition.py`
- [x] 3.3 Implement `lsp_find_references` tool in `mypi/tools/lsp/find_references.py`
- [x] 3.4 Implement `lsp_diagnostics` tool in `mypi/tools/lsp/diagnostics.py`
- [x] 3.5 Implement `lsp_rename` tool in `mypi/tools/lsp/rename.py`
- [x] 3.6 Implement `lsp_hover` tool in `mypi/tools/lsp/hover.py`

## 4. Integration

- [x] 4.1 Create `mypi/tools/lsp/__init__.py` with tool exports
- [x] 4.2 Update `mypi/tools/builtins.py` `make_builtin_registry()` to register LSP tools
- [x] 4.3 Add `requires_lsp: bool` flag to tool base for conditional registration

## 5. Testing

- [x] 5.1 Create unit tests for `LSPClientManager` in `tests/tools/lsp/test_client.py`
- [x] 5.2 Create unit tests for each LSP tool in `tests/tools/lsp/test_tools.py`
- [x] 5.3 Create integration test with mock LSP server
- [x] 5.4 Add test fixtures for sample Python code with various symbol types

## 6. Documentation

- [x] 6.1 Update README.md with LSP tools section
- [x] 6.2 Add LSP configuration examples to README.md
- [x] 6.3 Document required LSP server installation steps
