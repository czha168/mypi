## 1. Remove Corrupted Files

- [x] 1.1 Delete `codepi/core/rich_renderer.py` — contains Markdown prose instead of Python; real implementation is at `codepi/tui/rich_renderer.py` with no importers of the corrupted file
- [x] 1.2 Delete `ai/provider.py` (project root) — corrupted duplicate of `codepi/ai/provider.py` with literal `\n` escape sequences instead of actual newlines; no imports reference `ai.provider`
- [x] 1.3 Fix `tests/unit/test_attribution.py` — remove `*** End of File` trailer on line 62 that causes SyntaxError

## 2. Fix Provider Stream AsyncIterator Typing

- [x] 2.1 Change `LLMProvider.stream()` in `codepi/ai/provider.py` from `async def stream(...) -> AsyncIterator[ProviderEvent]` to `def stream(...) -> AsyncIterator[ProviderEvent]` (remove `async` keyword, keep return type)
- [x] 2.2 Update `OpenAICompatProvider.stream()` in `codepi/ai/openai_compat.py` from `async def` to `def` to match base class signature; remove the `# type: ignore[reportIncompatibleMethodOverride]` comment since the override will now be compatible
- [x] 2.3 Verify `async for event in provider.stream(...)` call sites still type-check: `agent_session.py` lines 286 and 465, `memory_extractor.py` line 64, `subagent.py` line 236

## 3. Fix LSP Client Type Errors

- [x] 3.1 Fix `codepi/tools/lsp/client.py`: implement missing abstract methods on `MypiLSPClient` — add `get_language_config` returning sensible defaults, add `check_server_compatibility` returning `True`, change `create_default_servers` to a `@classmethod` with correct return type annotation
- [x] 3.2 Fix `codepi/tools/lsp/client.py`: add `# type: ignore[attr-defined]` on the `WithReceivePublishDiagnostics` import line (line 75) since the `lsp_client` library lacks type stubs for this symbol
- [x] 3.3 Fix `codepi/tools/lsp/__init__.py`: change `"ToolRegistry"` string forward reference on line 16 to a proper import or use `from __future__ import annotations` (already present) — the issue is `ToolRegistry` is used in the function body, not a type annotation, so import it at function level (already done on line 17) and remove the string literal return type
- [x] 3.4 Fix `codepi/tools/lsp/goto_definition.py` line 45: add `# type: ignore[attr-defined]` for `client.request_definition_locations`
- [x] 3.5 Fix `codepi/tools/lsp/find_references.py` line 53: add `# type: ignore[attr-defined]` for `client.request_references`
- [x] 3.6 Fix `codepi/tools/lsp/hover.py` line 45: add `# type: ignore[attr-defined]` for `client.request_hover`
- [x] 3.7 Fix `codepi/tools/lsp/diagnostics.py` lines 41 and 47: add `# type: ignore[attr-defined]` for `client.notify_text_document_did_open` and `client.get_diagnostics`
- [x] 3.8 Fix `codepi/tools/lsp/rename.py` line 58: add `# type: ignore[attr-defined]` for `client.request_rename_edits`
- [x] 3.9 Fix `codepi/tools/lsp/rename.py` line 96: initialize `lines` before the edit loop (move `lines = content.splitlines(keepends=True)` outside the per-edit loop so it's always bound)

## 4. Fix Other Type Errors

- [x] 4.1 Fix `codepi/core/agent_session.py` line 261: add `# type: ignore[attr-defined]` after `e.retry_after` — the `hasattr` guard already exists but Pyright can't narrow `Exception` based on `hasattr`
- [x] 4.2 Fix `codepi/modes/interactive.py` line 68: change `TUIApp.renderer` type annotation in `codepi/tui/app.py` to `StreamingRenderer | RichRenderer` (Union) so the `self._app.renderer = self._renderer` assignment passes type checking; import `RichRenderer` from `codepi.tui.rich_renderer`
- [x] 4.3 Fix `codepi/extensions/loader.py` line 38: change `event.src_path.endswith(".py")` to `event.src_path.endswith((".py",))` to satisfy Pyright strict mode tuple expectation

## 5. Fix Test Type Errors

- [x] 5.1 Fix `tests/tui/test_rich_components.py` lines 30 and 35: add `assert inp._prompt_session is not None` guard before accessing `.completer` and `.complete_while_typing`
- [x] 5.2 Fix `tests/integration/test_mode_switching.py` line 55: add `assert plan_manager.state is not None` guard before accessing `.phase`

## 6. Verification

- [x] 6.1 Run `python3 -m py_compile` on all modified files to verify syntax correctness
- [x] 6.2 Run Pyright diagnostics on `codepi/` directory — expect zero errors
- [x] 6.3 Run Pyright diagnostics on `tests/` directory — expect zero errors
- [x] 6.4 Run `python3 -m pytest tests/ -x --tb=short` to verify no regressions in test suite
