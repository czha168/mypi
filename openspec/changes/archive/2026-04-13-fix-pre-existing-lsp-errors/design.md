## Context

The codebase (100 Python files) has 50+ Pyright errors that accumulated during rapid development. Errors fall into 6 categories:

1. **Corrupted files** (3 files) — non-Python content in `.py` files
2. **Third-party library type gaps** (8 errors) — `lsp_client` attributes not recognized by Pyright
3. **AsyncIterator typing mismatch** (4 errors) — `async def stream() -> AsyncIterator` creates a `Coroutine`, not an `AsyncIterator`
4. **Exception attribute narrowing** (1 error) — accessing `.retry_after` on bare `Exception`
5. **Type incompatibility** (2 errors) — `RichRenderer` vs `StreamingRenderer`, `endswith` literal type
6. **Optional member access in tests** (3 errors) — missing None checks

The project uses Pyright as its type checker (also the recommended LSP server). All errors are type-level only — runtime behavior is unaffected.

## Goals / Non-Goals

**Goals:**
- Achieve zero Pyright errors across `codepi/`, `tests/`, and `ai/`
- Fix root causes (wrong types, corrupted files) rather than suppress with `# type: ignore`
- Preserve all existing runtime behavior exactly

**Non-Goals:**
- Adding new features or refactoring logic
- Fixing errors in `openviking/` (C++ project, unrelated)
- Adding `# type: ignore` as a blanket solution (use only when third-party library provides no stubs)
- Enabling strict mode type checking (current mode is basic/standard)

## Decisions

### D1: Delete `codepi/core/rich_renderer.py` rather than fix it
**Decision**: Remove the corrupted file entirely.
**Rationale**: The file contains Markdown documentation, not Python code. The actual implementation is `codepi/tui/rich_renderer.py`. No code imports from `codepi.core.rich_renderer`.
**Alternative**: Replace with a re-export. Rejected — no consumers exist.

### D2: Fix `ai/provider.py` (root) by deleting or replacing
**Decision**: Delete `ai/provider.py` at the project root — it's a duplicate of `codepi/ai/provider.py` with corrupted newlines.
**Rationale**: The canonical provider lives at `codepi/ai/provider.py`. The root-level copy has `\n` as literal two-character sequences. No import references the root `ai/` package.

### D3: Fix `test_attribution.py` by removing `*** End of File` trailer
**Decision**: Delete the trailing `*** End of File` line.
**Rationale**: This is a copy-paste artifact. The test file ends at a valid `assert` statement; the trailer is syntactically invalid Python.

### D4: Add `py.typed` marker and type stubs for `lsp_client` locally
**Decision**: Use `# type: ignore[attr-defined]` on specific lines where `lsp_client` attributes aren't recognized, since the library doesn't ship type stubs.
**Rationale**: Creating full `.pyi` stubs for a third-party library is high effort with low ROI. Targeted `# type: ignore` comments on the 8 affected lines are precise and maintainable.
**Alternative**: Create `codepi/tools/lsp/lsp_client_stubs.pyi`. Rejected — too much maintenance for a small library.

### D5: Fix `MypiLSPClient` abstract implementation
**Decision**: Implement the two missing abstract methods (`get_language_config`, `check_server_compatibility`) with pass-through/sensible defaults, and change `create_default_servers` to a `@classmethod` returning `DefaultServers`.
**Rationale**: These are required by the `lsp_client.Client` base class. The runtime already works because the base class doesn't enforce them at runtime, but Pyright correctly flags them.

### D6: Fix AsyncIterator typing by changing abstract method signature
**Decision**: Change `LLMProvider.stream()` from `async def stream(...) -> AsyncIterator[ProviderEvent]` to `def stream(...) -> AsyncIterator[ProviderEvent]` (non-async). Update all concrete implementations to match.
**Rationale**: `async def` wrapping an async generator creates a `Coroutine` wrapper, which isn't directly iterable with `async for`. The method should be a regular method that returns an async iterator (typically an async generator). All call sites already use `async for event in provider.stream(...)`, so the runtime already depends on this contract.
**Alternative**: Keep `async def` and add `# type: ignore` at every call site. Rejected — wrong root cause, 4+ suppressions.

### D7: Fix `e.retry_after` with proper type narrowing
**Decision**: Keep the existing `hasattr(e, 'retry_after')` guard (which already exists) but add a type: ignore for the attribute access, since Pyright can't narrow `Exception` based on `hasattr`.
**Rationale**: The code already does `hasattr(e, 'retry_after')` before access. This is correct at runtime. Pyright just can't infer the narrowing.

### D8: Fix `RichRenderer` vs `StreamingRenderer` mismatch
**Decision**: Change `TUIApp.renderer` type annotation to `StreamingRenderer | RichRenderer` using a Union, or use a protocol.
**Rationale**: `interactive.py` assigns a `RichRenderer` to `TUIApp.renderer` which is typed as `StreamingRenderer`. Both classes have compatible interfaces (`start_turn`, `append_token`, `end_turn`, `render_tool_call`, `render_tool_result`, `render_user_message`, `render_error`, `render_info`). A Union type is the simplest fix.

### D9: Fix `endswith` type in loader.py
**Decision**: Change `event.src_path.endswith(".py")` to `event.src_path.endswith((".py",))`.
**Rationale**: Pyright's strict mode expects `endswith` to receive `Buffer | tuple[Buffer, ...]`. A single-element tuple satisfies this while keeping behavior identical.

### D10: Fix optional member access in tests
**Decision**: Add `assert ... is not None` guards before accessing optional attributes.
**Rationale**: Standard defensive pattern in tests. The attributes are expected to be set by the test setup, so asserting non-None is correct test behavior.

## Risks / Trade-offs

- **[Risk] Changing `stream()` from async to non-async could break subclasses** → Mitigation: Audit all concrete providers (`OpenAICompatProvider`) to ensure they also use non-async `def` with `yield`
- **[Risk] `# type: ignore` comments hide future real errors** → Mitigation: Use `# type: ignore[attr-defined]` (specific codes only), not blanket ignores
- **[Risk] Deleting `codepi/core/rich_renderer.py` could break unknown imports** → Mitigation: Grep for all imports of this module first — none exist
