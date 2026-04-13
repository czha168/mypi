## 1. Project Setup & Dependencies

- [x] 1.1 Create `codepi/tools/web/__init__.py` with lazy imports for `WebSearchTool`, `WebFetchTool`, `SiteScrapTool`
- [x] 1.2 Add `[web]` and `[web-full]` optional dependency groups to `pyproject.toml` (`ddgs>=9.0.0`, `httpx>=0.27.0`, `trafilatura>=2.0.0`, `scrapling>=0.4.6`, `scrapling[fetchers]>=0.4.6`)
- [x] 1.3 Install `[web]` deps in venv and verify imports work: `python3 -c "from codepi.tools.web import WebSearchTool"`

## 2. Shared Utilities

- [x] 2.1 Create `codepi/tools/web/storage.py` with `get_web_temp_dir(session_id)`, `url_to_slug(url, max_length=80)`, and `save_content(session_id, subdir, slug, content, extension)` functions
- [x] 2.2 Create `codepi/tools/web/detection.py` with `detect_bot_block(status_code, headers, html_content)`, `detect_js_only_page(html_content, extracted_text)`, and `needs_fallback(status_code, headers, html_content, extracted_text)` functions
- [x] 2.3 Write unit tests for `url_to_slug` (normal URLs, long URLs, special chars, query params, GitHub URLs)
- [x] 2.4 Write unit tests for `detect_bot_block` (Cloudflare markers, Akamai headers, generic blocks, clean responses)
- [x] 2.5 Write unit tests for `detect_js_only_page` (SPA frameworks, large HTML + tiny text, normal pages)

## 3. web_search Tool

- [x] 3.1 Create `codepi/tools/web/web_search.py` with `WebSearchTool` class extending `Tool`, with `name="web_search"`, `input_schema` (query + max_results), and async `execute()` using `ddgs`
- [x] 3.2 Implement result formatting: numbered entries with bold title, URL, and snippet
- [x] 3.3 Add `max_results` clamping to range 1-20
- [x] 3.4 Add dependency check: return `ToolResult(error=...)` with install instructions if `ddgs` not available
- [x] 3.5 Write unit tests for `WebSearchTool` (mock ddgs, verify output format, verify clamping, verify missing dep error)

## 4. web_fetch Tool

- [x] 4.1 Create `codepi/tools/web/web_fetch.py` with `WebFetchTool` class extending `Tool`, with `name="web_fetch"`, `input_schema` (url + max_length), and async `execute()`
- [x] 4.2 Implement HTTP fetch using `httpx.get()` with `follow_redirects=True`, custom User-Agent, 30s timeout
- [x] 4.3 Implement content extraction using `trafilatura.extract()` with fallback to `trafilatura.bare_extraction()` for metadata
- [x] 4.4 Implement content truncation at `max_length` with `[Content truncated...]` marker
- [x] 4.5 Implement failure detection pipeline: call `needs_fallback()` from `detection.py`, return appropriate error suggesting `site_scrap`
- [x] 4.6 Implement file saving via `save_content()` from `storage.py` with URL-slug naming and metadata header
- [x] 4.7 Implement output format: file path + content preview (first 500 chars) + metadata (title, author, site, date)
- [x] 4.8 Add dependency check: return error with install instructions if `httpx` or `trafilatura` not available
- [x] 4.9 Write unit tests for `WebFetchTool` (mock httpx+trafilatura, verify happy path, verify JS-only detection, verify bot-block detection, verify file saving, verify metadata output)

## 5. site_scrap Tool — Single Page Mode

- [x] 5.1 Create `codepi/tools/web/site_scrap.py` with `SiteScrapTool` class extending `Tool`, with `name="site_scrap"` and full `input_schema` (url, start_urls, selector, selector_type, fetcher, headless, max_pages, max_depth, allowed_domains, download_delay)
- [x] 5.2 Implement `fetcher="basic"` mode using `scrapling.Fetcher.get()` with error handling
- [x] 5.3 Implement `fetcher="auto"` escalation: try `Fetcher` → check for blocking → try `StealthyFetcher` → try `DynamicFetcher`, with graceful degradation when fetcher tiers are unavailable
- [x] 5.4 Implement `fetcher="stealthy"` using `StealthyFetcher.fetch()` with `headless=True`, `solve_cloudflare=True`
- [x] 5.5 Implement `fetcher="dynamic"` using `DynamicFetcher.fetch()` with `headless=True`
- [x] 5.6 Implement CSS selector extraction via `page.css(selector)` with `::text` and `::attr()` pseudo-element support
- [x] 5.7 Implement XPath selector extraction via `page.xpath(selector)`
- [x] 5.8 Implement no-selector mode: full page content extraction to markdown
- [x] 5.9 Implement file saving for single page results (.md for full content, .json for selector results)
- [x] 5.10 Add dependency check for `scrapling`, and specific checks for `StealthyFetcher`/`DynamicFetcher` availability

## 6. site_scrap Tool — Site Crawl Mode

- [x] 6.1 Implement crawl mode detection: when `start_urls` is provided, create a Scrapling Spider subclass dynamically
- [x] 6.2 Implement `max_depth` enforcement: track depth via `Request(meta={"depth": n})` and stop yielding `response.follow()` when depth exceeds limit
- [x] 6.3 Implement `max_pages` enforcement: counter in Spider that stops processing after N pages
- [x] 6.4 Implement `allowed_domains` auto-detection from `start_urls` when not explicitly provided
- [x] 6.5 Implement `download_delay` passthrough to Spider's `download_delay` config
- [x] 6.6 Implement selector extraction in Spider's `parse()` callback
- [x] 6.7 Implement result collection: capture `CrawlResult`, export to JSON/JSONL via `result.items.to_json()`
- [x] 6.8 Implement crawl statistics output (pages scraped, requests, success rate, elapsed time)

## 7. site_scrap Tool — GitHub Repo Mode

- [x] 7.1 Implement GitHub URL detection: match `github.com/{owner}/{repo}` patterns (with optional `/tree/{branch}/{path}`)
- [x] 7.2 Implement `git clone` to temp directory using `asyncio.create_subprocess_exec` with timeout
- [x] 7.3 Implement file tree listing: walk the cloned directory, format as tree output (up to 200 entries)
- [x] 7.4 Implement output format: clone path + file tree listing, indicating the LLM can use `read` tool to explore

## 8. Registry Integration

- [x] 8.1 Add web tool imports to `codepi/tools/builtins.py` in `make_builtin_registry()`, wrapped in try/except for graceful degradation when `[web]` not installed
- [x] 8.2 Verify all three tools appear in OpenAI function-calling schema when installed
- [x] 8.3 Verify codepi starts normally without `[web]` installed (no crashes, tools not registered)

## 9. Testing & Verification

- [x] 9.1 Write integration test: `web_search` with mocked ddgs returns formatted results
- [x] 9.2 Write integration test: `web_fetch` with mocked httpx saves markdown to temp dir with correct slug
- [x] 9.3 Write integration test: `web_fetch` detects JS-only page and returns fallback suggestion
- [x] 9.4 Write integration test: `site_scrap` basic fetcher returns page content
- [x] 9.5 Write integration test: `site_scrap` GitHub URL triggers git clone
- [x] 9.6 Run full test suite: `pytest tests/` — all existing tests pass, new tests pass
- [x] 9.7 Manual end-to-end test: run `codepi` with `[web]` installed, test all three tools interactively
