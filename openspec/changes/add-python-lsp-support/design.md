## Context

mypi is a minimalist terminal-based coding assistant with 7 built-in tools (read, write, edit, bash, find, grep, ls). It currently lacks semantic code understanding—navigation and analysis rely on text search rather than language-aware intelligence.

The tool system is clean and extensible:
- `Tool` base class with `name`, `description`, `input_schema`, and async `execute()`
- `ToolRegistry` manages tools and supports extension wrapping
- Tools can spawn subprocesses (see `BashTool` pattern)

**Stakeholders**: mypi users who want intelligent Python code navigation.

## Goals / Non-Goals

**Goals:**
- Add 5 LSP-powered tools: `lsp_goto_definition`, `lsp_find_references`, `lsp_diagnostics`, `lsp_rename`, `lsp_hover`
- Support Python LSP servers: pyright, pylsp, jedi-language-server (user-selectable)
- Auto-manage LSP server lifecycle (start on first use, graceful shutdown)
- Follow existing tool patterns (Tool base class, ToolRegistry)

**Non-Goals:**
- Multi-language LSP support (Python only for now)
- LSP completion/inline hints (can be added later)
- Custom LSP server configuration UI (use config file)

## Decisions

### D1: LSP Client Library

**Decision**: Use `lsp-client` (https://github.com/lsp-client/lsp-client)

**Rationale**:
- Production-ready async-first Python client
- Pre-built clients for Pyright, Basedpyright, Pyrefly
- Full LSP 3.17 specification coverage
- Active development (v0.3.9, Feb 2026)

**Alternatives Considered**:
- `pygls`: Primarily a server framework, client support is secondary
- `multilspy`: Microsoft's library, heavier dependency, designed for multi-language
- `pylspclient`: Less maintained, simpler but limited

### D2: Tool Granularity

**Decision**: 5 separate tools (one per LSP feature) rather than a single `lsp` tool

**Rationale**:
- LLM can reason about each tool's purpose independently
- Matches existing tool naming convention (e.g., `read`, `write`, `edit`)
- Clearer error messages and schema documentation
- Easier to track which LSP features are used

**Alternatives Considered**:
- Single `lsp` tool with `method` parameter: More flexible but less discoverable

### D3: Server Lifecycle Management

**Decision**: Lazy initialization with singleton pattern

**Rationale**:
- Start server on first LSP tool call, not at agent startup
- Reuse same server instance for all LSP operations
- Shutdown on agent session end or explicit cleanup
- Minimal impact when LSP tools aren't used

**Implementation**:
```python
class LSPClientManager:
    _instance: LSPClient | None = None
    
    @classmethod
    async def get_client(cls, workspace_root: str) -> LSPClient:
        if cls._instance is None:
            cls._instance = await cls._start_server(workspace_root)
        return cls._instance
```

### D4: Server Selection

**Decision**: Auto-detect with config override

**Priority order**:
1. Config-specified server (`config.lsp.server = "pyright"`)
2. First available on PATH: pyright → pylsp → jedi-language-server
3. Error if none found

**Rationale**: Good UX for beginners (just works), flexibility for advanced users.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| LSP server startup latency (1-3s) | Lazy init + show progress message on first call |
| Server crash mid-session | Auto-restart on next tool call with error recovery |
| Memory usage from long-running server | Document restart workflow; add `lsp_restart` tool |
| Version compatibility issues | Pin `lsp-client` version; test with popular server versions |
| Workspace changes not detected | Provide `lsp_restart` tool for manual refresh |

## Migration Plan

1. Add `lsp-client` to dependencies
2. Create `mypi/tools/lsp/` module with tools and client manager
3. Update `make_builtin_registry()` to include LSP tools
4. Add LSP config section to `config.py`
5. Graceful degradation: if no LSP server found, tools return helpful error message

**Rollback**: Remove LSP tools from registry, delete `mypi/tools/lsp/`, remove dependency.

## Open Questions

1. **Multiple workspace support**: Current design assumes single workspace. Need to decide if we support workspace switching mid-session.
   - *Recommendation*: Defer to future enhancement. Re-start server if workspace changes.

2. **Diagnostics caching**: Should we cache diagnostics between calls?
   - *Recommendation*: No caching initially. Fresh diagnostics each call for accuracy.
