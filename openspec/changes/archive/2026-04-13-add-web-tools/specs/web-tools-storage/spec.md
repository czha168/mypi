## ADDED Requirements

### Requirement: Session-scoped temp directory
The web tools SHALL use a session-scoped temp directory at `/tmp/codepi-{session_id}/` for all file output. The directory SHALL be created lazily on first use.

#### Scenario: Directory creation on first use
- **WHEN** any web tool saves a file for the first time in a session
- **THEN** the directory `/tmp/codepi-{session_id}/web/` or `/tmp/codepi-{session_id}/scrap/` SHALL be created with `parents=True, exist_ok=True`

#### Scenario: Separate subdirectories
- **WHEN** files are saved by different tools
- **THEN** `web_fetch` SHALL save to the `web/` subdirectory and `site_scrap` SHALL save to the `scrap/` subdirectory

### Requirement: URL-based slug file naming
Files SHALL be named using a URL-derived slug that is human-readable and filesystem-safe.

#### Scenario: Slug generation
- **WHEN** a URL `https://docs.python.org/3/library/asyncio.html` is fetched
- **THEN** the file SHALL be named `docs-python-org-3-library-asyncio-html.md`

#### Scenario: Slug length limit
- **WHEN** a URL produces a very long slug
- **THEN** the slug SHALL be truncated to a maximum of 80 characters

#### Scenario: Slug sanitization
- **WHEN** a URL contains special characters or query parameters
- **THEN** non-alphanumeric characters SHALL be replaced with hyphens, and the slug SHALL not start or end with a hyphen

### Requirement: File content structure
Saved markdown files SHALL include a header with metadata (source URL, fetch timestamp, page title) followed by the extracted content.

#### Scenario: Markdown file header
- **WHEN** a page is saved as markdown
- **THEN** the file SHALL start with:
  ```
  <!-- source: https://example.com/page -->
  <!-- fetched: 2026-04-13T10:30:00 -->
  <!-- title: Page Title -->

  # Page Title

  [content...]
  ```

### Requirement: Temp directory management utility
A shared `storage.py` module SHALL provide:
- `get_web_temp_dir(session_id)` — returns the temp dir path, creating it if needed
- `url_to_slug(url, max_length=80)` — converts URL to filesystem-safe slug
- `save_content(session_id, subdir, slug, content, extension)` — saves content to the appropriate temp subdirectory

#### Scenario: Utility functions are reusable
- **WHEN** `web_fetch` and `site_scrap` both need to save files
- **THEN** both SHALL use the same `storage.py` utility functions

### Requirement: No manual cleanup required
Temp directories SHALL rely on OS-level `/tmp` cleanup. No explicit garbage collection or eviction logic is required within codepi.

#### Scenario: Multiple sessions
- **WHEN** multiple codepi sessions run concurrently
- **THEN** each SHALL have its own temp directory (different session IDs) without conflicts
