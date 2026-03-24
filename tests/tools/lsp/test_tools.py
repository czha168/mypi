from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from mypi.tools.lsp.goto_definition import LSPGotoDefinitionTool
from mypi.tools.lsp.find_references import LSPFindReferencesTool
from mypi.tools.lsp.diagnostics import LSPDiagnosticsTool
from mypi.tools.lsp.rename import LSPRenameTool
from mypi.tools.lsp.hover import LSPHoverTool


class TestLSPGotoDefinitionTool:
    def test_tool_name(self):
        tool = LSPGotoDefinitionTool()
        assert tool.name == "lsp_goto_definition"

    def test_tool_has_required_schema_fields(self):
        tool = LSPGotoDefinitionTool()
        assert "file_path" in tool.input_schema["properties"]
        assert "line" in tool.input_schema["properties"]
        assert "character" in tool.input_schema["properties"]
        assert tool.input_schema["required"] == ["file_path", "line", "character"]

    @pytest.mark.asyncio
    async def test_returns_no_definition_found(self, tmp_path):
        tool = LSPGotoDefinitionTool()
        test_file = tmp_path / "test.py"
        test_file.write_text("def foo(): pass")

        mock_client = AsyncMock()
        mock_client.request_definition_locations = AsyncMock(return_value=[])

        with patch.object(
            LSPGotoDefinitionTool, "_get_client", return_value=mock_client
        ):
            result = await tool.execute(str(test_file), 1, 4)
            assert result.output == "No definition found."
            assert result.error is None


class TestLSPFindReferencesTool:
    def test_tool_name(self):
        tool = LSPFindReferencesTool()
        assert tool.name == "lsp_find_references"

    def test_tool_has_include_declaration_param(self):
        tool = LSPFindReferencesTool()
        assert "include_declaration" in tool.input_schema["properties"]

    @pytest.mark.asyncio
    async def test_returns_no_references_found(self, tmp_path):
        tool = LSPFindReferencesTool()
        test_file = tmp_path / "test.py"
        test_file.write_text("def foo(): pass")

        mock_client = AsyncMock()
        mock_client.request_references = AsyncMock(return_value=[])

        with patch.object(
            LSPFindReferencesTool, "_get_client", return_value=mock_client
        ):
            result = await tool.execute(str(test_file), 1, 4)
            assert result.output == "No references found."
            assert result.error is None


class TestLSPDiagnosticsTool:
    def test_tool_name(self):
        tool = LSPDiagnosticsTool()
        assert tool.name == "lsp_diagnostics"

    def test_tool_has_severity_param(self):
        tool = LSPDiagnosticsTool()
        assert "severity" in tool.input_schema["properties"]

    @pytest.mark.asyncio
    async def test_returns_no_diagnostics_found(self, tmp_path):
        tool = LSPDiagnosticsTool()
        test_file = tmp_path / "test.py"
        test_file.write_text("def foo(): pass")

        mock_client = AsyncMock()
        mock_client.notify_text_document_did_open = AsyncMock()
        mock_client.get_diagnostics = MagicMock(return_value=[])

        with patch.object(
            LSPDiagnosticsTool, "_get_client", return_value=mock_client
        ):
            result = await tool.execute(str(test_file))
            assert result.output == "No diagnostics found."
            assert result.error is None


class TestLSPRenameTool:
    def test_tool_name(self):
        tool = LSPRenameTool()
        assert tool.name == "lsp_rename"

    def test_tool_has_required_params(self):
        tool = LSPRenameTool()
        assert "new_name" in tool.input_schema["properties"]
        assert "dry_run" in tool.input_schema["properties"]
        assert "new_name" in tool.input_schema["required"]

    @pytest.mark.asyncio
    async def test_returns_no_changes_for_no_rename(self, tmp_path):
        tool = LSPRenameTool()
        test_file = tmp_path / "test.py"
        test_file.write_text("def foo(): pass")

        mock_client = AsyncMock()
        mock_client.request_rename_edits = AsyncMock(return_value=None)

        with patch.object(LSPRenameTool, "_get_client", return_value=mock_client):
            result = await tool.execute(str(test_file), 1, 4, "bar")
            assert result.output == "No changes to apply."
            assert result.error is None


class TestLSPHoverTool:
    def test_tool_name(self):
        tool = LSPHoverTool()
        assert tool.name == "lsp_hover"

    @pytest.mark.asyncio
    async def test_returns_no_hover_info(self, tmp_path):
        tool = LSPHoverTool()
        test_file = tmp_path / "test.py"
        test_file.write_text("def foo(): pass")

        mock_client = AsyncMock()
        mock_client.request_hover = AsyncMock(return_value=None)

        with patch.object(LSPHoverTool, "_get_client", return_value=mock_client):
            result = await tool.execute(str(test_file), 1, 4)
            assert result.output == "No hover information available."
            assert result.error is None
