from __future__ import annotations

from pathlib import Path

from codepi.tools.base import ToolResult
from codepi.tools.lsp.base import LSPTool


class LSPFindReferencesTool(LSPTool):
    name = "lsp_find_references"
    description = (
        "Find all references to a symbol at a given position in a Python file. "
        "Returns all locations where the symbol is used."
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
            "include_declaration": {
                "type": "boolean",
                "description": "Include the symbol's own declaration (default: true)",
            },
        },
        "required": ["file_path", "line", "character"],
    }

    async def execute(
        self,
        file_path: str,
        line: int,
        character: int,
        include_declaration: bool = True,
    ) -> ToolResult:
        try:
            from lsp_client import Position

            path = Path(file_path)
            workspace = self._find_workspace_root(path)

            client = await self._get_client(workspace)

            refs = await client.request_references(  # type: ignore[attr-defined]
                file_path=str(path),
                position=Position(line=line - 1, character=character),
            )

            if not refs:
                return ToolResult(output="No references found.")

            results = []
            for ref in refs:
                results.append(self._format_location(ref.uri, ref.range))
            return ToolResult(output="\n".join(results))
        except Exception as e:
            return ToolResult(error=str(e))

    def _find_workspace_root(self, path: Path) -> Path:
        for parent in path.parents:
            if (parent / "pyproject.toml").exists() or (parent / ".git").exists():
                return parent
        return path.parent
