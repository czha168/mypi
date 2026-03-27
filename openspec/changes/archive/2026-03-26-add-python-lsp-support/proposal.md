## Why

mypi currently relies on basic text-search tools (grep, find) for code navigation, lacking semantic understanding of Python code. This limits the agent's ability to perform intelligent code operations like jumping to definitions, finding all references, or understanding type errors—capabilities that modern LSP (Language Server Protocol) provides. Adding Python LSP support will make mypi significantly more effective at code analysis, refactoring, and debugging tasks.

## What Changes

- Add LSP client infrastructure for communicating with Python language servers
- Implement 5 new LSP-powered tools: `lsp_goto_definition`, `lsp_find_references`, `lsp_diagnostics`, `lsp_rename`, `lsp_hover`
- Add LSP server lifecycle management (auto-start/shutdown)
- Support for multiple Python LSP servers (pyright, pylsp, jedi-language-server)
- Automatic workspace initialization and configuration

## Capabilities

### New Capabilities

- `python-lsp-tools`: LSP-powered code intelligence tools for Python (go-to-definition, find-references, diagnostics, rename, hover)

### Modified Capabilities

None - this is a net-new feature addition.

## Impact

**New Dependencies:**
- `lsp-client` or `pygls` - Python LSP client library
- Requires a Python LSP server installed (pyright, pylsp, or jedi-language-server)

**Affected Code:**
- `mypi/tools/` - New LSP tool implementations
- `mypi/core/` - Potential LSP server lifecycle management
- `mypi/extensions/` - Optional extension for LSP server management
- `mypi/config.py` - LSP server configuration options

**API Changes:**
- 5 new tools exposed to the LLM: `lsp_goto_definition`, `lsp_find_references`, `lsp_diagnostics`, `lsp_rename`, `lsp_hover`
