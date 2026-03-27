"""Tool usage rules component for prompt composition."""

TOOL_USAGE_RULES = """
## Tool Usage

### File Operations
- Use `read` to read files instead of cat, head, tail, or sed
- Use `edit` for targeted string replacements in existing files
- Use `write` only when creating new files or when explicitly required
- Always preserve exact indentation when editing

### Search Operations
- Use `find` for glob pattern file searches
- Use `grep` for regex-based content search

### Shell Commands
- Use `bash` for system operations, git commands, and package management
- Run commands in the working directory by default
- Quote file paths containing spaces

### LSP Tools (when available)
- Use `lsp_goto_definition` to find where symbols are defined
- Use `lsp_find_references` to find all usages of a symbol
- Use `lsp_diagnostics` to check for errors before building
- Use `lsp_rename` to safely rename symbols across the workspace
"""


def format_tool_descriptions(tools_schema: list[dict]) -> str:
    """Format tool schema into human-readable descriptions.
    
    Args:
        tools_schema: OpenAI-format tools schema list
        
    Returns:
        Formatted tool descriptions string
    """
    lines = ["## Available Tools\n"]
    for tool in tools_schema:
        if tool.get("type") == "function":
            func = tool.get("function", {})
            name = func.get("name", "unknown")
            desc = func.get("description", "No description")
            lines.append(f"### {name}")
            lines.append(f"{desc}\n")
    return "\n".join(lines)
