from __future__ import annotations

from pathlib import Path

from codepi.tools.base import ToolResult
from codepi.tools.lsp.base import LSPTool


class LSPGotoDefinitionTool(LSPTool):
    name = "lsp_goto_definition"
    description = (
        "Jump to the definition of a symbol at a given position in a Python file. "
        "Returns file paths and line numbers where the symbol is defined."
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
            workspace = path.parent if not path.parent.joinpath("pyproject.toml").exists() else self._find_workspace_root(path)

            client = await self._get_client(workspace)

            locations = await client.request_definition_locations(
                file_path=str(path),
                position=Position(line=line - 1, character=character),
            )

            if not locations:
                return ToolResult(output="No definition found.")

            results = []
            for loc in locations:
                results.append(self._format_location(loc.uri, loc.range))
            return ToolResult(output="\n".join(results))
        except Exception as e:
            return ToolResult(error=str(e))

    def _find_workspace_root(self, path: Path) -> Path:
        for parent in path.parents:
            if (parent / "pyproject.toml").exists() or (parent / ".git").exists():
                return parent
        return path.parent
