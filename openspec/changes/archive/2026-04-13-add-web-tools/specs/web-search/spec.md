## ADDED Requirements

### Requirement: Web search using DuckDuckGo
The system SHALL provide a `web_search` tool that searches the web using DuckDuckGo via the `ddgs` library. The tool SHALL NOT require any API key or configuration.

#### Scenario: Basic search returns results
- **WHEN** the LLM calls `web_search` with `query="Python asyncio tutorial"`
- **THEN** the tool SHALL return a `ToolResult` with `output` containing a formatted list of search results, each with title, URL, and snippet

#### Scenario: Search with custom result count
- **WHEN** the LLM calls `web_search` with `query="FastAPI docs"` and `max_results=10`
- **THEN** the tool SHALL return up to 10 search results

#### Scenario: Search with no results
- **WHEN** the LLM calls `web_search` with a query that returns no results
- **THEN** the tool SHALL return a `ToolResult` with `output` containing "No results found for: {query}"

#### Scenario: Search when ddgs not installed
- **WHEN** the LLM calls `web_search` and the `ddgs` package is not installed
- **THEN** the tool SHALL return a `ToolResult` with `error` containing installation instructions: "Install web tools with: pip install codepi[web]"

### Requirement: Search result format
Each search result SHALL be formatted as a numbered entry with the page title (bold), URL, and a content snippet. Results SHALL be separated by blank lines for readability.

#### Scenario: Result formatting
- **WHEN** `web_search` returns 3 results
- **THEN** the output SHALL follow this format:
  ```
  1. **Page Title**
     URL: https://example.com/page
     Snippet: A brief description of the page content...

  2. **Another Title**
     URL: https://example.com/other
     Snippet: Another description...
  ```

### Requirement: Input schema
The `web_search` tool SHALL have an OpenAI function-calling schema with:
- `query` (string, required): The search query
- `max_results` (integer, optional, default 5): Maximum number of results, range 1-20

#### Scenario: Schema validation
- **WHEN** the tool registry generates the OpenAI schema for `web_search`
- **THEN** the schema SHALL include `query` as required and `max_results` as optional with default 5

### Requirement: Max results clamping
The tool SHALL clamp `max_results` to the range 1-20, regardless of the value passed.

#### Scenario: Max results exceeds upper bound
- **WHEN** the LLM calls `web_search` with `max_results=50`
- **THEN** the tool SHALL return at most 20 results

#### Scenario: Max results below lower bound
- **WHEN** the LLM calls `web_search` with `max_results=0`
- **THEN** the tool SHALL return at least 1 result
