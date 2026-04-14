"""Tool adapter helpers for ACP session adapter.

Pure functions for tool kind mapping, diff content extraction,
location extraction, and permission decision logic.
"""

from __future__ import annotations

from acp.schema import (
    FileEditToolCallContent,
    PermissionOption,
    ToolCallLocation,
)

from codepi.core.security import SecurityAction, SecurityDecision
from codepi.tools.base import ToolResult

TOOL_KIND_MAP: dict[str, str] = {
    "read": "read",
    "write": "edit",
    "edit": "edit",
    "bash": "execute",
    "find": "search",
    "grep": "search",
    "ls": "read",
    "lsp_diagnostics": "read",
    "lsp_goto_definition": "read",
    "lsp_find_references": "search",
    "lsp_hover": "read",
    "lsp_rename": "edit",
}


def map_tool_kind(tool_name: str) -> str:
    """Map internal tool name to ACP tool kind."""
    return TOOL_KIND_MAP.get(tool_name, "other")


def extract_locations(tool_name: str, arguments: dict) -> list[ToolCallLocation] | None:
    """Extract file locations from tool arguments for editor navigation.

    Returns a list of ToolCallLocation if a file path is found, else None.
    """
    path = arguments.get("file_path") or arguments.get("path")
    if path:
        return [ToolCallLocation(path=path)]
    return None


def extract_diff_content(
    tool_name: str,
    arguments: dict,
    result: ToolResult,
) -> list[FileEditToolCallContent] | None:
    """Extract diff content from edit/write tool results.

    Returns a list of FileEditToolCallContent for successful edit/write results,
    or None for other tools or failed results.
    """
    has_error = result.error is not None
    if has_error:
        return None

    if tool_name == "edit":
        path = arguments.get("file_path", "")
        old_text = arguments.get("old_string", "")
        new_text = arguments.get("new_string", "")
        return [
            FileEditToolCallContent(
                type="diff",
                path=path,
                old_text=old_text,
                new_text=new_text,
            )
        ]

    if tool_name == "write":
        path = arguments.get("file_path", "")
        new_text = arguments.get("content", "")
        return [
            FileEditToolCallContent(
                type="diff",
                path=path,
                old_text=None,
                new_text=new_text,
            )
        ]

    return None


def should_request_permission(
    tool_name: str,
    arguments: dict,
    security_decision: SecurityDecision,
) -> bool:
    """Determine if a tool call should trigger a permission request.

    Returns True only when the security decision is ASK.
    ALLOW and BLOCK decisions do not trigger permission requests.
    """
    return security_decision.action == SecurityAction.ASK


def build_permission_options() -> list[PermissionOption]:
    """Build the standard set of permission options for request_permission.

    Returns four options: Allow once, Allow always, Reject once, Reject always.
    """
    return [
        PermissionOption(option_id="allow_once", kind="allow_once", name="Allow once"),
        PermissionOption(option_id="allow_always", kind="allow_always", name="Allow always"),
        PermissionOption(option_id="reject_once", kind="reject_once", name="Reject once"),
        PermissionOption(option_id="reject_always", kind="reject_always", name="Reject always"),
    ]
