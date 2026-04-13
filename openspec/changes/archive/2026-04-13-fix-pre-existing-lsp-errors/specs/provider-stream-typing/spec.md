## ADDED Requirements

### Requirement: Provider stream method SHALL return AsyncIterator directly
The `LLMProvider.stream()` abstract method SHALL be declared as a regular method (not `async def`) returning `AsyncIterator[ProviderEvent]`. All concrete implementations SHALL follow this signature.

#### Scenario: Pyright recognizes stream return as async-iterable
- **WHEN** Pyright analyzes code using `async for event in provider.stream(...)`
- **THEN** no "CoroutineType is not iterable" errors are reported

#### Scenario: OpenAICompatProvider stream matches base signature
- **WHEN** Pyright analyzes `codepi/ai/openai_compat.py`
- **THEN** the `stream` method override is compatible with the base class `LLMProvider.stream`

### Requirement: Exception attribute access SHALL be type-safe
Code accessing custom attributes on caught exceptions (e.g., `e.retry_after`) SHALL use proper type narrowing or explicit type annotations to satisfy Pyright.

#### Scenario: Retry-after attribute access passes type checking
- **WHEN** Pyright analyzes the retry logic in `agent_session.py`
- **THEN** accessing `e.retry_after` after `hasattr` check produces no error

### Requirement: Renderer types SHALL be compatible
The `TUIApp.renderer` attribute SHALL accept both `StreamingRenderer` and `RichRenderer` instances via proper type annotation.

#### Scenario: RichRenderer assignment to TUIApp passes type checking
- **WHEN** `interactive.py` assigns `self._renderer` (a `RichRenderer`) to `self._app.renderer`
- **THEN** Pyright reports no type incompatibility

### Requirement: String endswith calls SHALL use correct argument types
The `endswith` method on strings SHALL receive arguments compatible with Pyright strict mode (tuple of strings, not bare string).

#### Scenario: Extension loader endswith passes type checking
- **WHEN** Pyright analyzes `event.src_path.endswith(...)` in `extensions/loader.py`
- **THEN** no argument type mismatch is reported
