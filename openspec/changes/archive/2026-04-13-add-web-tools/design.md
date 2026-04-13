## Context

codepi is a minimalist Python terminal coding assistant with 12 built-in tools (read, write, edit, bash, find, grep, ls + 5 LSP tools). It has zero web access — the LLM cannot search the web, fetch URLs, or scrape websites. All major competitors (Claude Code, Cursor, Continue) have built-in web tools.

The existing tool architecture is registry-based: tools extend the `Tool` ABC with `name`, `description`, `input_schema` (plain dict), and async `execute(**kwargs) -> ToolResult`. Registration happens in `make_builtin_registry()` in `codepi/tools/builtins.py`. No extra wiring needed beyond registration.

Current dependencies are minimal: `openai`, `rich`, `prompt_toolkit`, `watchdog`, `pyyaml`, `lsp-client`. The project uses optional dependency groups (`[dev]`) and Python 3.12+.

## Goals / Non-Goals

**Goals:**
- Add three web tools that work with any OpenAI-compatible LLM
- Zero-config default experience (no API keys for search)
- Progressive escalation: simple tools first, heavy tools only when needed
- Graceful degradation when optional dependencies are missing
- Session-scoped temp storage for fetched content
- Support single-page fetching, site-wide crawling, and GitHub repo cloning

**Non-Goals:**
- Multi-engine search support (Brave, Google API) — DuckDuckGo only for now
- Persistent web cache across sessions (temp dirs are session-scoped, OS-cleaned)
- MCP server integration for web tools
- Custom proxy configuration per tool call
- Rate limiting or request queuing within codepi
- PDF parsing, video transcription, or image analysis from fetched content

## Decisions

### Decision 1: Three-tool design with escalation chain

**Choice**: `web_search` → `web_fetch` → `site_scrap` escalation.

```
web_search: "find info about X"  →  results inline
web_fetch:  "read this URL"      →  saves markdown to temp file
site_scrap: "crawl this site"    →  Scrapling (heavy)
```

**Rationale**: Matches the LLM's natural reasoning pattern. `web_search` finds URLs. `web_fetch` reads a single page with simple Python. `site_scrap` handles the hard cases (JS rendering, anti-bot, site-wide crawling, GitHub repos). The LLM can start with `web_fetch` and escalate to `site_scrap` when it fails.

**Alternatives considered**:
- Single `web` tool with mode parameter — too many parameters, confusing for the LLM
- Two tools (search + fetch) only — doesn't handle crawling or anti-bot
- Five separate tools (search, fetch, scrape, crawl, clone) — too granular, LLM confusion

### Decision 2: Dependency tiers — `codepi[web]` vs `codepi[web-full]`

**Choice**: Two optional dependency groups.

| Group | Dependencies | What works |
|-------|-------------|------------|
| `codepi[web]` | `ddgs`, `httpx`, `trafilatura`, `scrapling` | All three tools. `site_scrap` uses basic Fetcher (HTTP only) |
| `codepi[web-full]` | everything in `[web]` + `scrapling[fetchers]` | StealthyFetcher (anti-bot/Cloudflare), DynamicFetcher (full Playwright) |

**Rationale**: Keeps the base `codepi[web]` fast to install (~seconds). Playwright + browser binaries (~100MB) are opt-in. Scrapling's base install includes the parser and basic `Fetcher` (HTTP with TLS fingerprinting), which covers most sites.

**Alternatives considered**:
- Single `[web]` with everything — too heavy, Playwright is 100MB+
- Three tiers (`[web]`, `[web-stealth]`, `[web-full]`) — unnecessary complexity
- No heavy tier — limits usefulness for anti-bot sites

### Decision 3: Temp directory strategy — session-scoped `/tmp`

**Choice**: `/tmp/codepi-{session_id}/web/` and `/tmp/codepi-{session_id}/scrap/`

**Rationale**: 
- Session-scoped: each codepi session gets its own temp dir, no cross-contamination
- `/tmp/`: OS-managed cleanup (macOS/Linux clean `/tmp` on boot or periodically)
- URL-slug file naming: human-readable when debugging (`docs-python-org-3-library-asyncio.md`)
- LLM can re-read saved files using the existing `read` tool

**Alternatives considered**:
- Persistent `~/.codepi/cache/web/` — adds cache management complexity, eviction policy, stale data
- Single flat temp dir — naming collisions, harder to debug
- In-memory only — large pages would blow up context window

### Decision 4: Failure detection heuristics for `web_fetch` fallback

**Choice**: Multi-level detection chain, returning clear error with "use site_scrap" suggestion.

Detection levels:
1. HTTP status (429, 403+Cloudflare, 503)
2. Bot-block markers in headers/content (`cf-mitigated: challenge`, "Just a moment...")
3. Trafilatura extraction failure (returns `None` or empty string)
4. JS-only page indicators (large HTML + tiny extracted text, SPA framework markers)
5. Low content ratio (HTML >50KB, text <200 chars)

**Rationale**: The LLM needs a clear signal about *why* `web_fetch` failed so it can decide whether to try `site_scrap`. Each failure returns a specific reason.

**Alternatives considered**:
- Silent automatic retry with Playwright — hides behavior from LLM, unpredictable latency
- No detection, just return empty content — LLM doesn't know to escalate
- Single boolean "needs_browser" — loses diagnostic information

### Decision 5: `site_scrap` uses Scrapling Spider framework for crawling

**Choice**: Dynamically create a Spider subclass for site-wide crawling, using `allowed_domains` for scope and manual depth tracking.

**Rationale**: Scrapling's Spider gives us concurrent requests, URL deduplication, pause/resume, robots.txt compliance, and streaming results for free. We wrap it with `max_pages` and `max_depth` limits (not built into Scrapling).

**Alternatives considered**:
- Custom crawler using Fetcher in a loop — reinventing the wheel, no dedup
- Scrapy — heavier, separate dependency, different API style
- Recursive httpx calls — no concurrency, no dedup, no robots.txt

### Decision 6: GitHub repo handling via `git clone`

**Choice**: Detect GitHub URLs in `site_scrap`, run `git clone` to temp dir, return file tree listing. LLM then uses existing `read` tool to explore.

**Rationale**: Most reliable approach for GitHub repos — no API limits, no auth needed for public repos, complete file access. The `bash` tool can already run `git clone`, but `site_scrap` packages it as a single tool call with file tree output.

**Alternatives considered**:
- Scrapling Spider on GitHub web UI — rate limited (60 req/hr unauthenticated), JS-rendered pages
- GitHub API — requires auth token, API complexity
- GitHub archive download — no git history, extra unpacking logic

### Decision 7: File structure — `codepi/tools/web/` package

**Choice**: New `codepi/tools/web/` package with separate modules per tool.

```
codepi/tools/web/
├── __init__.py       # exports + lazy imports
├── web_search.py     # WebSearchTool
├── web_fetch.py      # WebFetchTool  
├── site_scrap.py     # SiteScrapTool
├── detection.py      # failure detection heuristics
└── storage.py        # temp dir management, slug generation
```

**Rationale**: Separates concerns (each tool is self-contained), shared utilities (`detection.py`, `storage.py`) avoid duplication, lazy imports prevent ImportError when `[web]` not installed.

### Decision 8: Graceful degradation when dependencies missing

**Choice**: Each tool's `execute()` method attempts to import its dependencies and returns a clear `ToolResult(error=...)` with installation instructions if missing.

**Rationale**: Tools are registered in the registry regardless (so they appear in tool list), but fail at execution time with a helpful message. This means `codepi` without `[web]` still shows the tools exist but tells the user to install.

## Risks / Trade-offs

**[Risk] Scrapling dependency chain is heavy** → Mitigation: `[web]` installs base Scrapling (parser + basic Fetcher only). `[web-full]` is opt-in for Playwright. Users who only need search + simple fetch get a light install.

**[Risk] DuckDuckGo rate limiting or quality degradation** → Mitigation: `ddgs` supports multiple backends. If DDG quality drops, we can add Brave/Google as alternatives behind a `provider` config parameter without changing the tool API.

**[Risk] Trafilatura returns poor extraction for some sites** → Mitigation: The auto-detection logic catches empty/poor extractions and suggests `site_scrap`. Scrapling's parser can also extract content when trafilatura fails.

**[Risk] Temp dirs accumulate if many sessions run** → Mitigation: OS-managed `/tmp` cleanup. Each session gets one directory. Typical content is small (<100KB per page).

**[Risk] Scrapling Spider has no built-in depth limit** → Mitigation: We implement manual depth tracking by passing `depth` via `response.follow(meta={"depth": current_depth + 1})` and checking in `parse()`.

**[Risk] Playwright browser installation can fail on some systems** → Mitigation: Scrapling provides `scrapling install` command and Docker images. The tool returns clear error messages if browser is not available.
