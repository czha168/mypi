from __future__ import annotations

from pathlib import Path

from codepi.tools.base import ToolResult
from codepi.tools.lsp.base import LSPTool


class LSPRenameTool(LSPTool):
    name = "lsp_rename"
    description = (
        "Rename a symbol across all references in the workspace. "
        "Use dry_run=true to preview changes without applying them."
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
            "new_name": {
                "type": "string",
                "description": "The new name for the symbol",
            },
            "dry_run": {
                "type": "boolean",
                "description": "Preview changes without applying (default: true)",
            },
        },
        "required": ["file_path", "line", "character", "new_name"],
    }

    async def execute(
        self,
        file_path: str,
        line: int,
        character: int,
        new_name: str,
        dry_run: bool = True,
    ) -> ToolResult:
        try:
            from lsp_client import Position

            path = Path(file_path)
            workspace = self._find_workspace_root(path)

            client = await self._get_client(workspace)

            rename_result = await client.request_rename_edits(  # type: ignore[attr-defined]
                file_path=str(path),
                position=Position(line=line - 1, character=character),
                new_name=new_name,
            )

            if not rename_result or not rename_result.document_changes:
                return ToolResult(output="No changes to apply.")

            changes = []
            for change in rename_result.document_changes:
                file_uri = change.text_document.uri
                for edit in change.edits:
                    start = edit.range.start
                    changes.append(f"{file_uri}:{start.line + 1}:{start.character + 1}")

            if dry_run:
                preview = f"Preview of renaming to '{new_name}':\n" + "\n".join(changes)
                return ToolResult(output=preview)

            for change in rename_result.document_changes:
                file_path_resolved = Path(client.from_uri(change.text_document.uri))
                content = file_path_resolved.read_text()
                lines = content.splitlines(keepends=True)
                for edit in sorted(change.edits, key=lambda e: e.range.start.line, reverse=True):
                    start_line = edit.range.start.line
                    start_char = edit.range.start.character
                    end_line = edit.range.end.line
                    end_char = edit.range.end.character

                    if start_line == end_line:
                        line_content = lines[start_line]
                        lines[start_line] = (
                            line_content[:start_char] + edit.new_text + line_content[end_char:]
                        )
                    else:
                        pass

                file_path_resolved.write_text("".join(lines))

            return ToolResult(output=f"Renamed symbol to '{new_name}' in {len(changes)} locations.")
        except Exception as e:
            return ToolResult(error=str(e))

    def _find_workspace_root(self, path: Path) -> Path:
        for parent in path.parents:
            if (parent / "pyproject.toml").exists() or (parent / ".git").exists():
                return parent
        return path.parent
