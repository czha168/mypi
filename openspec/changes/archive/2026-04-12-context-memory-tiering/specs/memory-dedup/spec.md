## ADDED Requirements

### Requirement: Content fingerprint deduplication
Before storing a new memory, the system SHALL compute a SHA-256 hash of the normalized content and check for duplicates.

#### Scenario: Exact duplicate detected
- **WHEN** a candidate memory has the same SHA-256 hash as an existing memory
- **THEN** the system SHALL skip the candidate (dedup decision: `skip`)
- **AND** the existing memory's `access_count` is incremented

#### Scenario: No duplicate found
- **WHEN** a candidate memory has a unique SHA-256 hash
- **THEN** the system proceeds to keyword overlap check
- **AND** if keyword overlap is also below threshold, the memory is created (dedup decision: `create`)

### Requirement: Keyword overlap similarity check
For memories with different content hashes but potentially similar meaning, the system SHALL compute Jaccard similarity on token sets.

#### Scenario: High overlap triggers merge
- **WHEN** a candidate memory's Jaccard similarity with an existing memory exceeds 0.7
- **THEN** the system SHALL merge the candidate into the existing memory (dedup decision: `merge`)
- **AND** the merged content combines information from both, keeping the more detailed version

#### Scenario: Moderate overlap with conflicting information
- **WHEN** Jaccard similarity is between 0.4 and 0.7
- **AND** the candidate contradicts the existing memory
- **THEN** the system SHALL keep both memories (dedup decision: `create`)
- **AND** both memories are tagged with a `potentially_related` link

#### Scenario: Low overlap
- **WHEN** Jaccard similarity is below 0.4
- **THEN** the candidate is treated as new (dedup decision: `create`)

### Requirement: Dedup decision logging
All dedup decisions SHALL be logged for debugging and monitoring.

#### Scenario: Dedup event emitted
- **WHEN** a dedup decision is made (skip/create/merge)
- **THEN** the system emits a `MemoryDedupEvent` with: `candidate_hash`, `matched_hash` (if any), `similarity_score`, `decision`, `category`
- **AND** the event is logged at DEBUG level
