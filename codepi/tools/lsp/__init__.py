from __future__ import annotations

from typing import TYPE_CHECKING

from codepi.tools.lsp.goto_definition import LSPGotoDefinitionTool
from codepi.tools.lsp.find_references import LSPFindReferencesTool
from codepi.tools.lsp.diagnostics import LSPDiagnosticsTool
from codepi.tools.lsp.rename import LSPRenameTool
from codepi.tools.lsp.hover import LSPHoverTool

if TYPE_CHECKING:
    from codepi.tools.base import ToolRegistry

LSP_TOOLS = [
    LSPGotoDefinitionTool,
    LSPFindReferencesTool,
    LSPDiagnosticsTool,
    LSPRenameTool,
    LSPHoverTool,
]


def make_lsp_tool_registry() -> ToolRegistry:
    from codepi.tools.base import ToolRegistry
    reg = ToolRegistry()
    for tool_class in LSP_TOOLS:
        reg.register(tool_class())
    return reg
