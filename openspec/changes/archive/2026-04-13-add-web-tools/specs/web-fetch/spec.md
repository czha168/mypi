## ADDED Requirements

### Requirement: Fetch URL and extract markdown content
The system SHALL provide a `web_fetch` tool that fetches a URL using `httpx` and extracts clean markdown content using `trafilatura`. The extracted content SHALL be saved to a file in a session-scoped temp directory.

#### Scenario: Successful fetch and extraction
- **WHEN** the LLM calls `web_fetch` with `url="https://docs.python.org/3/library/asyncio.html"`
- **THEN** the tool SHALL fetch the page, extract markdown content, save it to `/tmp/codepi-{session_id}/web/{slug}.md`, and return a `ToolResult` with `output` containing the file path and a content preview (first 500 characters)

#### Scenario: Fetch with content length limit
- **WHEN** the LLM calls `web_fetch` with `url="..."` and `max_length=5000`
- **THEN** the saved content SHALL be truncated to approximately 5000 characters with a `[Content truncated...]` marker appended

#### Scenario: Fetch a page that requires JavaScript
- **WHEN** the LLM calls `web_fetch` for a JS-only page where trafilatura extracts less than 200 characters from HTML larger than 50KB
- **THEN** the tool SHALL return a `ToolResult` with `error` containing "Content could not be extracted (likely requires JavaScript rendering). Use the site_scrap tool for this URL."

#### Scenario: Fetch a page blocked by anti-bot
- **WHEN** the LLM calls `web_fetch` for a URL protected by Cloudflare or similar anti-bot system
- **THEN** the tool SHALL detect the block (via status code, headers like `cf-mitigated: challenge`, or HTML markers like "Just a moment...") and return a `ToolResult` with `error` containing "Page is protected by anti-bot system ({blocker_type}). Use the site_scrap tool with fetcher='stealthy' for this URL."

#### Scenario: Fetch when httpx or trafilatura not installed
- **WHEN** the LLM calls `web_fetch` and the required packages are not installed
- **THEN** the tool SHALL return a `ToolResult` with `error` containing "Install web tools with: pip install codepi[web]"

### Requirement: Auto-detection of failure conditions
The tool SHALL implement multi-level failure detection:
1. HTTP status code checks (429, 403+bot headers, 503)
2. Bot-block header/content markers (Cloudflare, Akamai, DataDome)
3. Trafilatura extraction failure (returns `None` or empty string)
4. JS-only page indicators (large HTML + tiny text, SPA framework markers)
5. Low content ratio (HTML >20KB, extracted text <300 chars)

#### Scenario: Detection returns specific reason
- **WHEN** any failure condition is detected
- **THEN** the error message SHALL include the specific reason (e.g., "js-only-page", "bot-block:cloudflare", "extraction-failed")

### Requirement: Output includes metadata
When extraction succeeds, the tool output SHALL include the page title, author (if available), site name (if available), and publication date (if available), sourced from trafilatura's metadata extraction.

#### Scenario: Metadata in output
- **WHEN** `web_fetch` successfully extracts a page with metadata
- **THEN** the output SHALL include lines like:
  ```
  **Title**: Async IO in Python
  **Author**: Author Name
  **Site**: docs.python.org
  **Saved to**: /tmp/codepi-abc123/web/docs-python-org-3-library-asyncio.md
  ```

### Requirement: URL following and redirects
The tool SHALL follow HTTP redirects (301, 302, 307, 308) automatically via `httpx`'s `follow_redirects=True`.

#### Scenario: Redirected URL
- **WHEN** `web_fetch` is called with a URL that redirects
- **THEN** the tool SHALL follow the redirect and extract content from the final URL

### Requirement: Input schema
The `web_fetch` tool SHALL have an OpenAI function-calling schema with:
- `url` (string, required): The URL to fetch
- `max_length` (integer, optional, default 10000): Maximum characters of extracted content

#### Scenario: Schema validation
- **WHEN** the tool registry generates the OpenAI schema for `web_fetch`
- **THEN** the schema SHALL include `url` as required and `max_length` as optional with default 10000
