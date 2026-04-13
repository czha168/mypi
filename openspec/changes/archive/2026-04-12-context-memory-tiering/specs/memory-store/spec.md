## ADDED Requirements

### Requirement: JSON-based memory file storage
Memories SHALL be stored as individual JSON files under `~/.codepi/memories/items/` with filenames derived from their content hash.

#### Scenario: Memory file creation
- **WHEN** a new memory is created after dedup
- **THEN** the system writes a JSON file at `~/.codepi/memories/items/{hash_prefix}.json`
- **AND** the file contains: `id` (UUID), `content` (string), `category` (enum), `topics` (list), `source_session_id` (string), `created_at` (ISO), `updated_at` (ISO), `access_count` (int, default 0)

#### Scenario: Memory file update on merge
- **WHEN** a merge dedup decision merges a candidate into an existing memory
- **THEN** the existing memory's JSON file is updated with merged content
- **AND** `updated_at` is set to current time
- **AND** `access_count` is incremented

### Requirement: Index manifest for fast retrieval
The system SHALL maintain an `index.json` manifest at `~/.codepi/memories/index.json` tracking all memories and their metadata.

#### Scenario: Index update on memory creation
- **WHEN** a new memory is stored
- **THEN** the system appends an entry to `index.json` with: `id`, `category`, `topics`, `access_count`, `updated_at`, `hotness_score`, `file_path`
- **AND** the index is written atomically (write to temp file, then rename)

#### Scenario: Index update on access
- **WHEN** a memory is retrieved for injection into a prompt
- **THEN** its `access_count` is incremented and `updated_at` is refreshed
- **AND** the hotness score is recalculated

### Requirement: Hotness scoring with sigmoid and time decay
Each memory SHALL have a `hotness_score` computed as: `sigmoid(log1p(access_count)) * time_decay(updated_at)`.

#### Scenario: Fresh memory with no accesses
- **WHEN** a memory is newly created with `access_count=0`
- **THEN** `hotness_score` = `sigmoid(0) * 1.0` = 0.5 (sigmoid(0) = 0.5, time_decay for current timestamp = 1.0)

#### Scenario: Frequently accessed memory
- **WHEN** a memory has `access_count=20` and was updated today
- **THEN** `hotness_score` = `sigmoid(log1p(20)) * ~1.0` ≈ 0.95 (high score)

#### Scenario: Old but popular memory
- **WHEN** a memory has `access_count=50` but was last accessed 14 days ago
- **THEN** `hotness_score` = `sigmoid(log1p(50)) * time_decay(14d)` ≈ 0.98 * 0.25 ≈ 0.245 (time decay dominates)

#### Scenario: Time decay half-life
- **WHEN** a memory's `updated_at` is exactly 7 days ago
- **THEN** `time_decay` returns exactly 0.5 (7-day half-life)

### Requirement: Memory eviction when capacity reached
The system SHALL enforce a configurable maximum memory count (default: 500).

#### Scenario: Eviction on capacity breach
- **WHEN** the number of stored memories exceeds the configured maximum
- **THEN** the system evicts the memory with the lowest `hotness_score`
- **AND** deletes the corresponding JSON file and removes it from the index
- **AND** memories in the `preferences` category are exempt from eviction

### Requirement: Topic-based retrieval for injection
The system SHALL retrieve memories matching a set of topic keywords, ranked by hotness score.

#### Scenario: Retrieve relevant memories
- **WHEN** the system receives a set of topic keywords from the current prompt
- **THEN** it returns memories whose `topics` list has at least one keyword in common with the query
- **AND** results are sorted by `hotness_score` descending
- **AND** at most 20 memories are returned
