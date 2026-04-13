## ADDED Requirements

### Requirement: Web tools registered in builtin registry
The three web tools (`web_search`, `web_fetch`, `site_scrap`) SHALL be registered in `make_builtin_registry()` alongside existing built-in tools. Registration SHALL use lazy imports to avoid ImportError when web dependencies are not installed.

#### Scenario: Tools available when codepi[web] installed
- **WHEN** `make_builtin_registry()` is called and `codepi[web]` is installed
- **THEN** the registry SHALL include `web_search`, `web_fetch`, and `site_scrap` tools in addition to the existing 7 built-in tools

#### Scenario: Graceful handling when codepi[web] not installed
- **WHEN** `make_builtin_registry()` is called and `codepi[web]` is NOT installed
- **THEN** the import SHALL be wrapped in try/except, logging a debug message, and the three web tools SHALL NOT be registered (no crash)

#### Scenario: Tools appear in OpenAI function schema
- **WHEN** the tool registry generates the OpenAI function-calling schema
- **THEN** all registered web tools SHALL appear in the schema list with their names, descriptions, and input schemas

### Requirement: Web tools in separate package
Web tools SHALL live in `codepi/tools/web/` as a Python package, separate from `codepi/tools/builtins.py`.

#### Scenario: Package structure
- **WHEN** the web tools module is imported
- **THEN** it SHALL be importable as `from codepi.tools.web import WebSearchTool, WebFetchTool, SiteScrapTool`

### Requirement: Execution-time dependency check
Each web tool's `execute()` method SHALL attempt to import its required dependencies at the start of execution and return a clear error if they are missing.

#### Scenario: web_search without ddgs
- **WHEN** `web_search.execute()` is called and `ddgs` is not importable
- **THEN** it SHALL return `ToolResult(error="web_search requires ddgs. Install with: pip install codepi[web]")`

#### Scenario: web_fetch without httpx
- **WHEN** `web_fetch.execute()` is called and `httpx` is not importable
- **THEN** it SHALL return `ToolResult(error="web_fetch requires httpx and trafilatura. Install with: pip install codepi[web]")`

#### Scenario: site_scrap without scrapling
- **WHEN** `site_scrap.execute()` is called and `scrapling` is not importable
- **THEN** it SHALL return `ToolResult(error="site_scrap requires scrapling. Install with: pip install codepi[web]")`

### Requirement: Optional dependency groups in pyproject.toml
Two optional dependency groups SHALL be added to `pyproject.toml`:
- `[web]`: `ddgs>=9.0.0`, `httpx>=0.27.0`, `trafilatura>=2.0.0`, `scrapling>=0.4.6`
- `[web-full]`: inherits `[web]` + `scrapling[fetchers]>=0.4.6`

#### Scenario: pip install codepi[web]
- **WHEN** a user runs `pip install codepi[web]`
- **THEN** all lightweight web dependencies SHALL be installed, enabling all three tools with basic functionality

#### Scenario: pip install codepi[web-full]
- **WHEN** a user runs `pip install codepi[web-full]`
- **THEN** all `[web]` dependencies plus Playwright and stealth browser dependencies SHALL be installed, enabling `site_scrap` with `StealthyFetcher` and `DynamicFetcher`

### Requirement: No impact on base installation
Installing codepi without `[web]` SHALL NOT install any new dependencies. Existing tools and functionality SHALL be completely unaffected.

#### Scenario: Base install unchanged
- **WHEN** codepi is installed without `[web]` or `[web-full]`
- **THEN** the dependency list SHALL be identical to the current release, and all existing tools SHALL work normally
