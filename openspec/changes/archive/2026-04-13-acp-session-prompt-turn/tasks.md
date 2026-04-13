## 1. AgentSession Cancellation Support

- [x] 1.1 Add `_cancelled: bool = False` field to `AgentSession.__init__()`, add `cancel()` method that sets `_cancelled = True`, and add `is_cancelled` property that returns `_cancelled`
- [x] 1.2 Reset `_cancelled` to `False` at the start of `AgentSession.prompt()` (before `_is_idle = False`)
- [x] 1.3 Write unit test: test that `cancel()` sets `is_cancelled` to `True`, and that `prompt()` resets it to `False`

## 2. Content Block Helpers

- [x] 2.1 Create `codepi/acp/content.py` with four builder functions: `text_content(text)`, `resource_content(uri, text, mime_type=None)`, `diff_content(path, old_text, new_text)`, `terminal_content(terminal_id)` per the `acp-content-blocks` spec
- [x] 2.2 Write unit tests for all four content block builders verifying the dict structure matches spec

## 3. ACPSessionAdapter Core

- [x] 3.1 Create `codepi/acp/session_adapter.py` with `ACPSessionAdapter.__init__(session_id, cwd, config, conn)` storing all params and initializing `_agent_session = None`, `_tool_call_counter = 0`, `_current_tool_call_id = None`, `_cancel_event = asyncio.Event()`
- [x] 3.2 Implement `_setup()` lazy init method that creates `LLMProvider`, `SessionManager`, `ToolRegistry`, `AgentSession` (using config and factories), and wires callbacks (`on_token`, `on_tool_call`, `on_tool_result`, `on_error`)
- [x] 3.3 Implement `_send_update(update)` that calls `await self._conn.session_update(session_id=self.session_id, update=update)`
- [x] 3.4 Implement `_on_token(text)` callback that calls `asyncio.create_task(self._send_update(update_agent_message(text_block(text))))` using ACP SDK helpers
- [x] 3.5 Implement `_on_tool_call(name, arguments)` callback: increment counter, generate tool call ID, map tool kind via `_map_tool_kind()`, extract locations via `_extract_locations()`, send `start_tool_call` notification, store current tool call ID
- [x] 3.6 Implement `_on_tool_result(name, result)` callback: send `update_tool_call` with `status: "completed"` if no error, `status: "failed"` if error, with text content
- [x] 3.7 Implement `_on_error(message)` callback: send `agent_message_chunk` with `"Error: " + message` text
- [x] 3.8 Implement `_map_tool_kind(tool_name)` static method with the 12-entry mapping table from the `acp-session-adapter` spec, defaulting to `"other"`
- [x] 3.9 Implement `_extract_locations(tool_name, arguments)` static method that extracts `file_path` or `path` from arguments and returns `[{"path": ...}]` or `None`
- [x] 3.10 Implement `_create_provider()`, `_create_tool_registry()`, `_load_extensions()` factory methods that use the config to instantiate codepi internals

## 4. ACPSessionAdapter Prompt & Cancel

- [x] 4.1 Implement `run_prompt(prompt_blocks)` method: extract text from content blocks (text and resource types), join with newlines, call `_setup()`, clear cancel event, call `AgentSession.prompt()`, return `PromptResponse(stop_reason="end_turn")` on success
- [x] 4.2 Handle cancellation in `run_prompt()`: catch `CancelledError`, return `PromptResponse(stop_reason="cancelled")`
- [x] 4.3 Handle exceptions in `run_prompt()`: catch other exceptions, log error, return `PromptResponse(stop_reason="refusal")`
- [x] 4.4 Implement `cancel()` method: set internal cancel event, call `AgentSession.cancel()` if session is initialized

## 5. CodepiAgent Integration

- [x] 5.1 Change `CodepiAgent._sessions` type from `dict[str, dict[str, Any]]` to `dict[str, ACPSessionAdapter]`
- [x] 5.2 Update `new_session()` to create `ACPSessionAdapter(session_id, cwd, self._config, self._conn)` and store in `_sessions`
- [x] 5.3 Replace `prompt()` stub with real implementation: look up adapter in `_sessions`, raise `ValueError` if not found, delegate to `adapter.run_prompt(prompt)`, return the `PromptResponse`
- [x] 5.4 Replace `cancel()` stub with real implementation: look up adapter in `_sessions`, log warning and return if not found, delegate to `adapter.cancel()`

## 6. Testing

- [x] 6.1 Write unit test: `ACPSessionAdapter._map_tool_kind` returns correct ToolKind for all 12 known tools and `"other"` for unknown
- [x] 6.2 Write unit test: `ACPSessionAdapter._extract_locations` extracts path from `file_path` and `path` arguments, returns `None` for tools without paths
- [x] 6.3 Write unit test: mock `AgentSession` callbacks and verify correct ACP notifications are sent via mock connection
- [x] 6.4 Write unit test: `CodepiAgent.prompt()` delegates to adapter, raises `ValueError` for unknown session
- [x] 6.5 Write unit test: `CodepiAgent.cancel()` delegates to adapter, handles unknown session gracefully
- [x] 6.6 Run full test suite: `python3 -m pytest tests/ -x` and verify no regressions
