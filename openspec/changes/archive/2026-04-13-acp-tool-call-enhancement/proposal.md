## Why

Phase 1–2 of the ACP migration established the transport layer and basic prompt turn flow, but tool calls still lack two critical ACP features: **permission requests** for dangerous operations and **diff content** for file edits. Without these, editors/IDEs cannot render file changes inline or gate risky operations behind user confirmation — both are baseline expectations of the ACP spec's `tool_call` lifecycle.

## What Changes

- **Permission flow**: Dangerous tool calls (`write`, `edit`, `bash`) and security monitor ASK decisions will trigger `session/request_permission` to the ACP client, blocking execution until the user responds. The existing security monitor (`SecurityAction.ASK`) will be routed through ACP's bidirectional permission protocol instead of the current synchronous callback.
- **Diff content**: `write` and `edit` tool results will include `FileEditToolCallContent` (type `diff`) in `tool_call_update` notifications, enabling editors to render before/after diffs inline.
- **File locations**: Tool call start notifications will populate `locations` with file paths and line numbers for `read`, `edit`, `write`, `grep`, and `find` tools, enabling editors' "follow along" navigation.
- **New module**: `codepi/acp/tool_adapter.py` — extracts permission logic, tool kind mapping, diff extraction, and location extraction from the monolithic `session_adapter.py` into a focused helper module.

## Capabilities

### New Capabilities
- `acp-permission-flow`: Bidirectional permission request/response via `session/request_permission`, integrating with codepi's existing `SecurityMonitor` and ACP's `PermissionOption`/`SelectedPermissionOutcome` types.
- `acp-tool-diff-content`: File edit diff content in `tool_call_update` notifications using `FileEditToolCallContent`, with before/after text for `edit` and `write` tools.

### Modified Capabilities
- `acp-session-adapter`: Enhance `_on_tool_call` to integrate permission flow and enrich `_on_tool_result` with diff content; extract helper logic into `tool_adapter.py`.

## Impact

- **Files modified**: `codepi/acp/session_adapter.py` (permission integration in tool call lifecycle, diff content in results)
- **Files created**: `codepi/acp/tool_adapter.py` (permission decision logic, diff extraction, location extraction)
- **Dependencies**: Uses existing `acp.schema.PermissionOption`, `acp.schema.RequestPermissionResponse`, `acp.schema.FileEditToolCallContent` — no new packages
- **APIs**: `Client.request_permission()` call added to the ACP session adapter
- **Security**: Existing `SecurityMonitor` decisions (ALLOW/BLOCK/ASK) remain authoritative; ACP permission flow only adds the transport layer for ASK decisions
