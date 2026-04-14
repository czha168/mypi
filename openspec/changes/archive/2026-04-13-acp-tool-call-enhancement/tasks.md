## 1. Tool Adapter Module

- [x] 1.1 Create `codepi/acp/tool_adapter.py` with `TOOL_KIND_MAP` dict (move from session_adapter), `should_request_permission(tool_name, arguments, security_decision) -> bool`, `build_permission_options() -> list[PermissionOption]`, `extract_diff_content(tool_name, arguments, result) -> list[FileEditToolCallContent] | None`, `extract_locations(tool_name, arguments) -> list[ToolCallLocation] | None`
- [x] 1.2 Move `_TOOL_KIND_MAP` and `_extract_locations` from `session_adapter.py` into `tool_adapter.py`; update imports in `session_adapter.py` to use the new functions

## 2. Diff Content in Tool Call Updates

- [x] 2.1 Update `_on_tool_result` in `session_adapter.py` to call `tool_adapter.extract_diff_content()` when `tool_name` is `edit` or `write` and result has no error; include the returned `FileEditToolCallContent` in the `ToolCallUpdate` content list alongside the existing text content
- [x] 2.2 Verify: run existing tests, then write a unit test in `tests/acp/test_tool_adapter.py` confirming `extract_diff_content` returns correct diff dicts for `edit` (with old_text/new_text) and `write` (with old_text=None) and `None` for other tools

## 3. Security Monitor Integration

- [x] 3.1 Update `ACPSessionAdapter._setup()` to create a `SecurityMonitor` from `config.security` and pass it as `security_monitor` to the `AgentSession` constructor
- [x] 3.2 Add `_on_security_ask(self, reason: str, rule_id: str) -> bool` method to `ACPSessionAdapter` that calls `self._conn.request_permission()` with the current tool call ID, kind, status="pending", and standard permission options; return `True` on `allowed` outcome, `False` on `denied` outcome or timeout (120s)
- [x] 3.3 Wire `self._agent_session._on_security_ask = self._on_security_ask` in `_setup()` — but note `AgentSession._on_security_ask` is currently sync; change it to accept an async callback by making the call in `_stream_turn` use `await self._on_security_ask(...)` when the callback is coroutine-capable (use `asyncio.iscoroutinefunction` check)
- [x] 3.4 Write unit tests: mock `Client.request_permission` returning `allowed` → callback returns `True`; mock returning `denied` → callback returns `False`; mock timeout → callback returns `False`

## 4. Integration Testing

- [x] 4.1 Add integration test in `tests/acp/test_session_adapter_permission.py`: create `ACPSessionAdapter` with mock `Client`, mock `AgentSession` that fires `on_tool_call` for `bash` with `git push`, verify `request_permission` is called before tool execution completes
- [x] 4.2 Add integration test verifying diff content: fire `on_tool_result` for `edit` tool with successful result, verify `ToolCallUpdate` contains `FileEditToolCallContent` with correct path/oldText/newText
- [x] 4.3 Run full test suite (`python3 -m pytest tests/acp/`) and verify all existing Phase 1–2 tests still pass

## 5. Cleanup

- [x] 5.1 Remove any dead code from `session_adapter.py` after extraction to `tool_adapter.py` (ensure `_TOOL_KIND_MAP` and `_extract_locations` static method are fully moved, not duplicated)
- [x] 5.2 Verify `LSP diagnostics` clean on `tool_adapter.py`, `session_adapter.py`, and `agent.py` (no type errors)
