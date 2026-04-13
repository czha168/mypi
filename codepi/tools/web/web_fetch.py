from __future__ import annotations
from datetime import datetime
from codepi.tools.base import Tool, ToolResult
from codepi.tools.web.detection import needs_fallback
from codepi.tools.web.storage import url_to_slug, save_content


class WebFetchTool(Tool):
    name = "web_fetch"
    description = (
        "Fetch a URL and extract clean markdown content. Saves content to a temp file. "
        "Returns file path, preview, and metadata. If the page requires JavaScript or is blocked by anti-bot, returns an error suggesting site_scrap."
    )

    input_schema = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "The URL to fetch"},
            "max_length": {
                "type": "integer",
                "description": "Maximum characters of extracted content (default 10000)",
            },
        },
        "required": ["url"],
    }

    async def execute(self, url: str, max_length: int = 10000) -> ToolResult:  # type: ignore[reportIncompatibleMethodOverride]
        try:
            import httpx  # type: ignore[import]
            import trafilatura  # type: ignore[import]
        except ImportError:
            return ToolResult(error="web_fetch requires httpx and trafilatura. Install with: pip install codepi[web]")

        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=30.0,
                headers={"User-Agent": "Mozilla/5.0 (compatible; codepi/0.1)"},
            ) as client:
                response = await client.get(url)
        except Exception as e:
            return ToolResult(error=str(e))

        status = response.status_code
        html = response.text
        headers = dict(response.headers)

        # Early detection for bot-block or other blockers
        block_reason = needs_fallback(status, headers, html, "")
        if block_reason:
            if isinstance(block_reason, str) and block_reason.startswith("bot-block"):
                return ToolResult(
                    error=f"Page is protected by anti-bot system ({block_reason}). Use the site_scrap tool with fetcher='stealthy' for this URL."
                )
            if block_reason == "rate-limited":
                return ToolResult(error="Rate limited by the server. Try again later or use site_scrap tool.")

        # Attempt extraction
        extracted = trafilatura.extract(html) or ""

        # Post-extraction blockers check
        post_reason = needs_fallback(status, headers, html, extracted)
        if post_reason:
            if post_reason == "js-only-page":
                return ToolResult(error="Content could not be extracted (likely requires JavaScript rendering). Use the site_scrap tool for this URL.")
            if post_reason == "extraction-failed":
                return ToolResult(error="Content extraction failed (empty or unusable content). Use the site_scrap tool for this URL.")
            return ToolResult(error=f"Fetch failed ({post_reason}). Use the site_scrap tool for this URL.")

        # Metadata extraction
        try:
            metadata = trafilatura.bare_extraction(html) or {}
        except Exception:
            metadata = {}

        title = metadata.get("title", "") if isinstance(metadata, dict) else ""
        author = metadata.get("author", "") if isinstance(metadata, dict) else ""
        sitename = metadata.get("sitename", "") if isinstance(metadata, dict) else ""
        date = metadata.get("date", "") if isinstance(metadata, dict) else ""

        # Truncate content if needed
        if max_length and len(extracted) > max_length:
            extracted = extracted[:max_length] + "\n\n[Content truncated...]"

        # Build markdown content with metadata header
        now = datetime.now().isoformat(timespec="seconds")
        header = f"<!-- source: {url} -->\n<!-- fetched: {now} -->\n"
        if title:
            header += f"<!-- title: {title} -->\n\n# {title}\n\n"
        else:
            header += "\n"

        file_content = header + extracted

        # Save to temp file using storage utilities
        session_id = "default"
        slug = url_to_slug(url)
        file_path = save_content(session_id, "web", slug, file_content, "md")

        preview = extracted[:500]
        output_lines = [f"**Saved to**: {file_path}"]
        if title:
            output_lines.append(f"**Title**: {title}")
        if author:
            output_lines.append(f"**Author**: {author}")
        if sitename:
            output_lines.append(f"**Site**: {sitename}")
        if date:
            output_lines.append(f"**Date**: {date}")
        output_lines.append("")
        output_lines.append("--- Preview (first 500 chars) ---")
        output_lines.append(preview)

        return ToolResult(output="\n".join(output_lines))
