from __future__ import annotations
from codepi.tools.base import Tool, ToolResult


class WebSearchTool(Tool):
    name = "web_search"
    description = "Search the web using DuckDuckGo. Returns a list of results with title, URL, and snippet. No API key required."
    input_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The search query"},
            "max_results": {"type": "integer", "description": "Maximum number of results (1-20, default 5)"},
        },
        "required": ["query"],
    }

    # type: ignore[reportIncompatibleMethodOverride]
    async def execute(self, query: str, max_results: int = 5) -> ToolResult:
        # Lazy import to avoid hard dependency when the tool is registered but not used.
        try:
            from ddgs import DDGS  # type: ignore[import]
        except ImportError:
            return ToolResult(error="web_search requires ddgs. Install with: pip install codepi[web]")

        # Clamp results to allowed range
        max_results = max(1, min(20, max_results))

        try:
            results = DDGS().text(query, max_results=max_results)
        except Exception as e:
            return ToolResult(error=str(e))

        if not results:
            return ToolResult(output=f"No results found for: {query}")

        # Format results: numbered list with bold title, URL and snippet
        lines = []
        for idx, item in enumerate(results[:max_results], start=1):
            title = item.get("title", "")
            href = item.get("href", "")
            body = item.get("body", "")
            lines.append(f"{idx}. **{title}**")
            lines.append(f"   URL: {href}")
            lines.append(f"   Snippet: {body}")
            lines.append("")

        output = "\n".join(lines).rstrip()
        return ToolResult(output=output)
