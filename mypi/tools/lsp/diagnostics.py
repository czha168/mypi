from __future__ import annotations

from pathlib import Path

from mypi.tools.base import ToolResult
from mypi.tools.lsp.base import LSPTool


class LSPDiagnosticsTool(LSPTool):
    name = "lsp_diagnostics"
    description = (
        "Get diagnostics (errors, warnings, hints) for Python files. "
        "Returns type errors, linting issues, and other problems."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Absolute path to the Python file",
            },
            "severity": {
                "type": "string",
                "description": "Filter by severity: 'error', 'warning', 'information', 'hint', or 'all'",
            },
        },
        "required": ["file_path"],
    }

    SEVERITY_MAP = {"error": 1, "warning": 2, "information": 3, "hint": 4}

    async def execute(
        self, file_path: str, severity: str = "all"
    ) -> ToolResult:
        try:
            path = Path(file_path)
            workspace = self._find_workspace_root(path)

            client = await self._get_client(workspace)

            await client.notify_text_document_did_open(
                file_path=str(path),
                text=path.read_text(),
                language_id="python",
            )

            diags = client.get_diagnostics(str(path))

            if not diags:
                return ToolResult(output="No diagnostics found.")

            severity_filter = self.SEVERITY_MAP.get(severity.lower())

            results = []
            for diag in diags:
                if severity_filter and getattr(diag, "severity", 1) != severity_filter:
                    continue
                results.append(self._format_diagnostic(diag))

            return ToolResult(output="\n".join(results) if results else "No diagnostics found.")
        except Exception as e:
            return ToolResult(error=str(e))

    def _find_workspace_root(self, path: Path) -> Path:
        for parent in path.parents:
            if (parent / "pyproject.toml").exists() or (parent / ".git").exists():
                return parent
        return path.parent
