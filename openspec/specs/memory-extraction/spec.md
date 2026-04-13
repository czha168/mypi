## ADDED Requirements

### Requirement: Post-compaction memory extraction
After a tiered compaction completes, the system SHALL extract reusable knowledge items from the compacted conversation segment and persist them to the memory store.

#### Scenario: Successful extraction after compaction
- **WHEN** a tiered compaction entry is created
- **THEN** the system analyzes the L1 overview and conversation messages
- **AND** extracts knowledge items categorized as: `decisions`, `patterns`, `file-knowledge`, `preferences`
- **AND** each item contains: `content` (string), `category` (enum), `topics` (list of keywords), `source_session_id` (string), `created_at` (ISO timestamp)

#### Scenario: Extraction when no meaningful knowledge found
- **WHEN** the conversation contains only trivial exchanges (greetings, simple questions with no code changes)
- **THEN** the system SHALL skip extraction and produce zero knowledge items
- **AND** no error is raised

### Requirement: Four-category memory taxonomy
Extracted memories SHALL be classified into exactly one of four categories.

#### Scenario: Decision extraction
- **WHEN** the conversation contains an explicit or implicit technical choice (e.g., "using SQLite over JSON", "switching to async")
- **THEN** the system extracts a `decisions` memory with the decision rationale

#### Scenario: Pattern extraction
- **WHEN** the conversation shows a recurring code pattern or idiom (e.g., error handling style, test structure)
- **THEN** the system extracts a `patterns` memory describing the pattern

#### Scenario: File-knowledge extraction
- **WHEN** the conversation reveals project-specific knowledge about files, functions, or architecture (e.g., "auth logic is in core/security.py")
- **THEN** the system extracts a `file-knowledge` memory mapping the knowledge to file paths

#### Scenario: Preference extraction
- **WHEN** the user states a preference (e.g., "always use type hints", "prefer pytest over unittest")
- **THEN** the system extracts a `preferences` memory recording the preference

### Requirement: Memory extraction uses LLM
The extraction pipeline SHALL use a single LLM call with the L1 overview to identify and extract knowledge items.

#### Scenario: LLM extraction call
- **WHEN** extraction runs after compaction
- **THEN** the system sends the L1 overview to the LLM with a structured extraction prompt
- **AND** the prompt requests JSON output listing extracted items with category, content, and topics
- **AND** if the LLM response is malformed, the system logs a warning and skips extraction for this cycle
