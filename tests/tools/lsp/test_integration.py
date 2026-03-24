from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch


class MockLSPClient:
    """Mock LSP client for integration testing."""

    def __init__(self):
        self._documents: dict[str, str] = {}
        self._diagnostics: dict[str, list] = {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def notify_text_document_did_open(self, file_path: str, text: str, language_id: str):
        self._documents[file_path] = text

    async def request_definition_locations(self, file_path: str, position):
        return []

    async def request_references(self, file_path: str, position):
        return []

    async def request_hover(self, file_path: str, position):
        return None

    async def request_rename_edits(self, file_path: str, position, new_name: str):
        return None

    def get_diagnostics(self, file_path: str) -> list:
        return self._diagnostics.get(file_path, [])

    def from_uri(self, uri: str) -> Path:
        return Path(uri.replace("file://", ""))


class TestLSPIntegration:
    @pytest.mark.asyncio
    async def test_tool_returns_graceful_error_without_lsp_server(self, tmp_path):
        from mypi.tools.lsp.goto_definition import LSPGotoDefinitionTool

        test_file = tmp_path / "test.py"
        test_file.write_text("def foo(): pass")

        tool = LSPGotoDefinitionTool()

        with patch.object(
            tool.__class__.__bases__[0],
            "_get_client",
            side_effect=RuntimeError("No Python LSP server found"),
        ):
            result = await tool.execute(str(test_file), 1, 4)
            assert result.error is not None
            assert "No Python LSP server found" in result.error

    @pytest.mark.asyncio
    async def test_goto_definition_with_mock_server(self, sample_python_project):
        from mypi.tools.lsp.goto_definition import LSPGotoDefinitionTool

        mock_client = MockLSPClient()

        tool = LSPGotoDefinitionTool()
        main_py = sample_python_project / "src" / "main.py"

        with patch.object(tool, "_get_client", return_value=mock_client):
            result = await tool.execute(str(main_py), 5, 20)
            assert result.error is None
            assert result.output == "No definition found."

    @pytest.mark.asyncio
    async def test_find_references_with_mock_server(self, sample_python_project):
        from mypi.tools.lsp.find_references import LSPFindReferencesTool

        mock_client = MockLSPClient()

        tool = LSPFindReferencesTool()
        models_py = sample_python_project / "src" / "models.py"

        with patch.object(tool, "_get_client", return_value=mock_client):
            result = await tool.execute(str(models_py), 1, 7)
            assert result.error is None
            assert result.output == "No references found."

    @pytest.mark.asyncio
    async def test_diagnostics_with_mock_server(self, sample_python_project):
        from mypi.tools.lsp.diagnostics import LSPDiagnosticsTool

        mock_client = MockLSPClient()

        tool = LSPDiagnosticsTool()
        models_py = sample_python_project / "src" / "models.py"

        with patch.object(tool, "_get_client", return_value=mock_client):
            result = await tool.execute(str(models_py))
            assert result.error is None
            assert result.output == "No diagnostics found."

    @pytest.mark.asyncio
    async def test_hover_with_mock_server(self, sample_python_project):
        from mypi.tools.lsp.hover import LSPHoverTool

        mock_client = MockLSPClient()

        tool = LSPHoverTool()
        models_py = sample_python_project / "src" / "models.py"

        with patch.object(tool, "_get_client", return_value=mock_client):
            result = await tool.execute(str(models_py), 1, 7)
            assert result.error is None
            assert result.output == "No hover information available."

    @pytest.mark.asyncio
    async def test_rename_dry_run_with_mock_server(self, sample_python_project):
        from mypi.tools.lsp.rename import LSPRenameTool

        mock_client = MockLSPClient()

        tool = LSPRenameTool()
        models_py = sample_python_project / "src" / "models.py"

        with patch.object(tool, "_get_client", return_value=mock_client):
            result = await tool.execute(str(models_py), 1, 7, "Person", dry_run=True)
            assert result.error is None
            assert result.output == "No changes to apply."
