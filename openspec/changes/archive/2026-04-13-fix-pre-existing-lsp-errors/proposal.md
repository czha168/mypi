## Why

The codebase has 50+ pre-existing Pyright type errors across production code and tests that were introduced during rapid development. These errors range from corrupted files (Markdown content in `.py` files) to legitimate type mismatches in the LSP client integration and provider stream API. Leaving them unfixed masks real bugs, degrades IDE experience, and makes it impossible to enforce type checking in CI.

## What Changes

- **Delete corrupted stub** `codepi/core/rich_renderer.py` — contains Markdown prose instead of Python; the real implementation lives in `codepi/tui/rich_renderer.py`
- **Fix corrupted file** `ai/provider.py` (root level) — single-line file with literal `\n` escape sequences instead of actual newlines
- **Fix corrupted test** `tests/unit/test_attribution.py` — ends with `*** End of File` literal text
- **Fix LSP client type errors** in `codepi/tools/lsp/`:
  - Add missing `type: ignore` comments or proper stubs for `lsp_client` third-party library attributes (`request_definition_locations`, `request_references`, `request_hover`, `request_rename_edits`, `notify_text_document_did_open`, `get_diagnostics`)
  - Fix `MypiLSPClient` abstract class implementation (implement `get_language_config`, `check_server_compatibility`; fix `create_default_servers` classmethod/return-type mismatch)
  - Fix `WithReceivePublishDiagnostics` import path
  - Fix `ToolRegistry` forward reference in `__init__.py`
  - Fix `lines` possibly-unbound in `rename.py`
- **Fix AsyncIterator type issues** in `memory_extractor.py`, `agent_session.py`, `subagent.py` — provider `.stream()` returns `AsyncIterator` but `async def` wraps it in `CoroutineType`; need to adjust the abstract method signature or call site
- **Fix Exception attribute access** in `agent_session.py` — `e.retry_after` on bare `Exception`
- **Fix type mismatch** in `interactive.py` — `RichRenderer` not assignable to `StreamingRenderer` attribute
- **Fix `endswith` type** in `extensions/loader.py` — Pyright strict mode string literal issue
- **Fix optional member access** in test files (`test_rich_components.py`, `test_mode_switching.py`)

## Capabilities

### New Capabilities
- `lsp-type-safety`: Proper type annotations and stubs for the `lsp_client` third-party library integration
- `provider-stream-typing`: Correct `AsyncIterator` vs `Coroutine` typing for the provider stream API

### Modified Capabilities
_None_ — no spec-level behavior changes; only type annotations, corrupted file cleanup, and defensive checks

## Impact

- **Affected code**: `codepi/core/`, `codepi/tools/lsp/`, `codepi/extensions/`, `codepi/modes/`, `codepi/tui/`, `codepi/ai/`, `tests/`, `ai/`
- **Dependencies**: No new dependencies; fixes leverage existing `typing`, `lsp_client`, and `rich`
- **Runtime behavior**: Zero change — all fixes are type-level, defensive, or deleting dead/corrupted files
- **Test impact**: 3 test files need minor defensive fixes; no test logic changes
