from __future__ import annotations

from pathlib import Path

from codepi.tools.base import ToolResult
from codepi.tools.lsp.base import LSPTool


class LSPHoverTool(LSPTool):
    name = "lsp_hover"
    description = (
        "Get type information and documentation for a symbol at a given position. "
        "Returns the inferred type, signature, and any docstring."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Absolute path to the Python file",
            },
            "line": {
                "type": "integer",
                "description": "1-based line number",
            },
            "character": {
                "type": "integer",
                "description": "0-based character offset on the line",
            },
        },
        "required": ["file_path", "line", "character"],
    }

    async def execute(
        self, file_path: str, line: int, character: int
    ) -> ToolResult:
        try:
            from lsp_client import Position

            path = Path(file_path)
            workspace = self._find_workspace_root(path)

            client = await self._get_client(workspace)

            hover_result = await client.request_hover(
                file_path=str(path),
                position=Position(line=line - 1, character=character),
            )

            if not hover_result or not hover_result.contents:
                return ToolResult(output="No hover information available.")

            contents = hover_result.contents
            if hasattr(contents, "value"):
                return ToolResult(output=contents.value)
            elif hasattr(contents, "kind"):
                return ToolResult(output=f"```{contents.kind}\n{contents.value}\n```")
            elif isinstance(contents, str):
                return ToolResult(output=contents)
            elif isinstance(contents, list):
                parts = []
                for item in contents:
                    if hasattr(item, "value"):
                        parts.append(item.value)
                    elif isinstance(item, str):
                        parts.append(item)
                return ToolResult(output="\n".join(parts))

            return ToolResult(output=str(contents))
        except Exception as e:
            return ToolResult(error=str(e))

    def _find_workspace_root(self, path: Path) -> Path:
        for parent in path.parents:
            if (parent / "pyproject.toml").exists() or (parent / ".git").exists():
                return parent
        return path.parent
