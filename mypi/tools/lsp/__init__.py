from mypi.tools.lsp.goto_definition import LSPGotoDefinitionTool
from mypi.tools.lsp.find_references import LSPFindReferencesTool
from mypi.tools.lsp.diagnostics import LSPDiagnosticsTool
from mypi.tools.lsp.rename import LSPRenameTool
from mypi.tools.lsp.hover import LSPHoverTool

LSP_TOOLS = [
    LSPGotoDefinitionTool,
    LSPFindReferencesTool,
    LSPDiagnosticsTool,
    LSPRenameTool,
    LSPHoverTool,
]


def make_lsp_tool_registry() -> "ToolRegistry":
    from mypi.tools.base import ToolRegistry
    reg = ToolRegistry()
    for tool_class in LSP_TOOLS:
        reg.register(tool_class())
    return reg
