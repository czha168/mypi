from __future__ import annotations

from abc import abstractmethod
from pathlib import Path

from mypi.tools.base import Tool, ToolResult
from mypi.tools.lsp.client import LSPClientManager


class LSPTool(Tool):
    async def _get_client(self, workspace_root: str | Path):
        return await LSPClientManager.get_client(workspace_root)

    def _format_location(self, uri: str, range_obj) -> str:
        start = range_obj.start
        return f"{uri}:{start.line + 1}:{start.character + 1}"

    def _format_diagnostic(self, diag) -> str:
        severity_map = {1: "error", 2: "warning", 3: "information", 4: "hint"}
        severity = severity_map.get(getattr(diag, "severity", 1), "error")
        start = diag.range.start
        return f"{severity}: {diag.message} (line {start.line + 1}, col {start.character + 1})"
