## ADDED Requirements

### Requirement: Single page scraping with progressive fetchers
The system SHALL provide a `site_scrap` tool that can scrape a single URL using Scrapling with progressive fetcher tiers: basic HTTP (`Fetcher`), anti-bot stealth (`StealthyFetcher`), and full browser automation (`DynamicFetcher`).

#### Scenario: Basic HTTP scraping
- **WHEN** the LLM calls `site_scrap` with `url="https://example.com"` and `fetcher="basic"`
- **THEN** the tool SHALL use Scrapling's `Fetcher.get()` to fetch the page and return the page object with extracted content saved to temp dir

#### Scenario: Auto-fetcher escalation
- **WHEN** the LLM calls `site_scrap` with `fetcher="auto"` (default)
- **THEN** the tool SHALL first try `Fetcher`, and if the response indicates blocking (empty content, challenge page), escalate to `StealthyFetcher` (if available), then `DynamicFetcher` (if available)

#### Scenario: Stealthy fetcher for anti-bot pages
- **WHEN** the LLM calls `site_scrap` with `fetcher="stealthy"` and `scrapling[fetchers]` is installed
- **THEN** the tool SHALL use `StealthyFetcher.fetch()` with `headless=True` and `solve_cloudflare=True`

#### Scenario: Stealthy fetcher not available
- **WHEN** the LLM calls `site_scrap` with `fetcher="stealthy"` and `scrapling[fetchers]` is NOT installed
- **THEN** the tool SHALL return a `ToolResult` with `error` containing "Stealthy/Dynamic fetchers require scrapling[fetchers]. Install with: pip install codepi[web-full]"

### Requirement: CSS/XPath selector extraction
The tool SHALL support extracting specific elements from scraped pages using CSS selectors or XPath expressions.

#### Scenario: Extract with CSS selector
- **WHEN** the LLM calls `site_scrap` with `url="..."` and `selector=".product-title"` and `selector_type="css"`
- **THEN** the tool SHALL extract matching elements and return their text content as structured data

#### Scenario: Extract with XPath selector
- **WHEN** the LLM calls `site_scrap` with `selector="//div[@class='price']/text()"` and `selector_type="xpath"`
- **THEN** the tool SHALL extract matching elements using XPath

#### Scenario: No selector returns full page
- **WHEN** the LLM calls `site_scrap` without a `selector` parameter
- **THEN** the tool SHALL return the full page content extracted to markdown

### Requirement: Site-wide crawling via Spider framework
The tool SHALL support site-wide crawling using Scrapling's Spider framework when `start_urls` is provided.

#### Scenario: Basic site crawl
- **WHEN** the LLM calls `site_scrap` with `start_urls=["https://example.com/"]`
- **THEN** the tool SHALL create a Scrapling Spider, crawl the site within `max_pages` and `max_depth` limits, and save results as JSON to temp dir

#### Scenario: Crawl with depth limit
- **WHEN** the LLM calls `site_scrap` with `start_urls=["https://example.com/"]` and `max_depth=2`
- **THEN** the tool SHALL only follow links up to 2 levels deep from the start URL

#### Scenario: Crawl with page limit
- **WHEN** the LLM calls `site_scrap` with `max_pages=20`
- **THEN** the tool SHALL stop crawling after fetching 20 pages

#### Scenario: Crawl with domain restriction
- **WHEN** the LLM calls `site_scrap` with `start_urls=["https://example.com/"]` and `allowed_domains=["example.com"]`
- **THEN** the tool SHALL only follow links within the specified domain(s)

#### Scenario: Auto-detect allowed domains
- **WHEN** the LLM calls `site_scrap` with `start_urls` but no `allowed_domains`
- **THEN** the tool SHALL automatically extract domains from `start_urls` and restrict crawling to those domains

#### Scenario: Crawl with selector extraction
- **WHEN** the LLM calls `site_scrap` with `start_urls` and `selector=".article h2"`
- **THEN** the tool SHALL extract matching elements from each crawled page and include them in the results

### Requirement: GitHub repository cloning
The tool SHALL detect GitHub repository URLs and clone them to the temp directory instead of web scraping.

#### Scenario: Clone a GitHub repo
- **WHEN** the LLM calls `site_scrap` with `url="https://github.com/user/repo"`
- **THEN** the tool SHALL detect the GitHub URL, run `git clone` to a temp directory, and return the clone path with a file tree listing

#### Scenario: Clone a specific branch or path
- **WHEN** the LLM calls `site_scrap` with `url="https://github.com/user/repo/tree/main/src"`
- **THEN** the tool SHALL clone the repo and indicate the relevant subdirectory in the output

#### Scenario: Clone returns file tree
- **WHEN** a GitHub repo is cloned
- **THEN** the output SHALL include a tree-style listing of files (up to 200 entries) and the full path to the clone directory, so the LLM can use the `read` tool to explore

### Requirement: Output saved to temp directory
All scraping results SHALL be saved to the session-scoped temp directory at `/tmp/codepi-{session_id}/scrap/`. Single page results SHALL be saved as `.md` (markdown) or `.json` (if selectors used). Crawl results SHALL be saved as `.json` or `.jsonl`.

#### Scenario: Single page output file
- **WHEN** `site_scrap` scrapes a single page
- **THEN** the result SHALL be saved to `/tmp/codepi-{session_id}/scrap/{slug}.md` (or `.json` if selectors were used)

#### Scenario: Crawl output file
- **WHEN** `site_scrap` completes a site crawl
- **THEN** the results SHALL be saved to `/tmp/codepi-{session_id}/scrap/{slug}.json`

### Requirement: Crawl statistics in output
When crawling completes, the output SHALL include crawl statistics: pages scraped, total requests, success rate, and elapsed time.

#### Scenario: Stats in output
- **WHEN** a site crawl completes
- **THEN** the output SHALL include lines like:
  ```
  Pages scraped: 15
  Total requests: 18
  Success rate: 94.4%
  Elapsed: 12.3s
  Results saved to: /tmp/codepi-abc123/scrap/example-com.json
  ```

### Requirement: Input schema
The `site_scrap` tool SHALL have an OpenAI function-calling schema with:
- `url` (string, optional): URL for single page scraping or GitHub repo
- `start_urls` (array of strings, optional): Starting URLs for site crawling
- `selector` (string, optional): CSS or XPath selector for element extraction
- `selector_type` (string, optional, default "css"): "css" or "xpath"
- `fetcher` (string, optional, default "auto"): "auto", "basic", "stealthy", or "dynamic"
- `headless` (boolean, optional, default true): Run browser in headless mode
- `max_pages` (integer, optional, default 50): Maximum pages for crawling
- `max_depth` (integer, optional, default 3): Maximum crawl depth
- `allowed_domains` (array of strings, optional): Domains to restrict crawling to
- `download_delay` (number, optional, default 1.0): Seconds between requests

At least one of `url` or `start_urls` MUST be provided.

#### Scenario: Schema validation
- **WHEN** the tool registry generates the OpenAI schema for `site_scrap`
- **THEN** the schema SHALL list `url` and `start_urls` as optional but at least one required
