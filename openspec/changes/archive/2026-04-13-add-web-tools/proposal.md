## Why

codepi currently has no web access — the LLM cannot search the web or fetch live content. Every other major coding assistant (Claude Code, Cursor, Continue) supports web search and URL fetching as built-in capabilities. Without these tools, codepi cannot look up documentation, research APIs, read web articles, or scrape websites on the user's behalf.

## What Changes

- **Add `web_search` tool**: Search the web using DuckDuckGo (via `ddgs` library). Returns a list of results with title, URL, and snippet. Zero configuration — no API key required.
- **Add `web_fetch` tool**: Fetch a single URL and extract clean markdown content using `httpx` + `trafilatura`. Saves content to a session-scoped temp directory. Auto-detects when a page needs JavaScript rendering or is blocked by anti-bot systems, and returns a clear error suggesting `site_scrap` as fallback.
- **Add `site_scrap` tool**: Scrape websites using Scrapling with progressive fetcher tiers (basic HTTP → stealthy anti-bot → full Playwright browser). Supports three modes: single page scraping, site-wide crawling (via Scrapling Spider framework), and GitHub repo cloning. Saves results to temp directory.
- **Add optional `codepi[web]` dependency group**: Lightweight web tools (`ddgs`, `httpx`, `trafilatura`, `scrapling`). Graceful degradation when dependencies are missing — tools return installation instructions.
- **Add optional `codepi[web-full]` dependency group**: Everything in `[web]` plus `scrapling[fetchers]` for Playwright-based stealthy/dynamic browser automation.

## Capabilities

### New Capabilities
- `web-search`: Web search tool using DuckDuckGo — zero-config, no API key
- `web-fetch`: Single URL fetching with content extraction to markdown, failure auto-detection for JS-only and bot-blocked pages
- `site-scrap`: Site scraping with Scrapling — single page extraction, site-wide crawling via Spider framework, GitHub repo cloning; progressive fetcher tiers (basic/stealthy/dynamic)
- `web-tools-storage`: Session-scoped temp directory management for web tool output — URL-slug file naming, structured temp dirs (`web/` and `scrap/` subdirs)
- `web-tools-registry`: Registration of web tools in `make_builtin_registry()` with graceful import handling when `codepi[web]` is not installed

### Modified Capabilities
- (none — no existing specs are changing)

## Impact

- **New files**: `codepi/tools/web/__init__.py`, `web_search.py`, `web_fetch.py`, `site_scrap.py`, `detection.py`, `storage.py`
- **Modified files**: `codepi/tools/builtins.py` (add web tool registration), `pyproject.toml` (add `[web]` and `[web-full]` optional dependency groups)
- **New dependencies** (optional): `ddgs>=9.0.0`, `httpx>=0.27.0`, `trafilatura>=2.0.0`, `scrapling>=0.4.6`, `scrapling[fetchers]>=0.4.6`
- **API surface**: Three new tools exposed to the LLM via OpenAI function-calling schema
- **No breaking changes**: All new tools are opt-in via `[web]` extra; existing codepi installations are unaffected
- **Testing**: Requires `venv` for all testing, Ollama model `gpt-oss:20b-128k` for end-to-end tests
