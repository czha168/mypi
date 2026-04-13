## ADDED Requirements

### Requirement: Three-tier compaction entries
When auto-compaction triggers, the system SHALL produce a `tiered_compaction` entry containing three tiers: L0 (abstract, ~50 tokens), L1 (overview, ~500 tokens), and L2 (reference to original messages in session file).

#### Scenario: Auto-compaction produces tiered entry
- **WHEN** token usage exceeds the compaction threshold (default 80% of context window)
- **THEN** the system generates a `tiered_compaction` SessionEntry with fields `{l0: "<keywords/topics>", l1: "<structured overview>", summary: "<l1 content>"}`
- **AND** the `summary` field is set to L1 content for backward compatibility

#### Scenario: Tiered entry preserves topic structure
- **WHEN** the conversation covers multiple distinct topics (e.g., auth fix, test refactor, config update)
- **THEN** L1 organizes information by topic with section headers
- **AND** L0 lists the key topics and entities as a keyword index

### Requirement: Bottom-up summarization within session tree
The compaction system SHALL summarize from leaf entries upward. Each compaction entry summarizes only the messages in its subtree, not the entire session history.

#### Scenario: Linear session compaction
- **WHEN** a session with 50 messages triggers compaction
- **THEN** the system walks from the current leaf to the most recent compaction point (or root)
- **AND** summarizes only the messages in that segment
- **AND** the compaction entry is appended as a child of the current leaf

#### Scenario: Branched session preserves branch context
- **WHEN** compaction triggers on a branch that diverged from the main path
- **THEN** the summary covers only messages on the active branch path
- **AND** messages from other branches are not included in the summary

### Requirement: Backward compatibility with flat compaction
The system SHALL continue to support sessions containing existing `compaction` entries with flat summaries.

#### Scenario: Loading old session with flat compaction
- **WHEN** `build_context()` encounters a `compaction` entry (type="compaction")
- **THEN** it treats the `summary` field as L1 content
- **AND** generates an L0 by truncating to the first sentence
- **AND** context reconstruction works identically to current behavior

#### Scenario: New tiered compaction entry in context build
- **WHEN** `build_context()` encounters a `tiered_compaction` entry
- **AND** token budget is sufficient (>2000 tokens available for context)
- **THEN** it uses L1 (overview) as the summary injection
- **WHEN** token budget is tight (<500 tokens available)
- **THEN** it uses L0 (abstract) as the summary injection

### Requirement: Structured LLM prompt for tiered generation
The compaction system SHALL use a single structured LLM call that produces both L0 and L1 tiers simultaneously.

#### Scenario: Tiered compaction LLM call
- **WHEN** compaction triggers
- **THEN** the system sends a prompt requesting structured output with two sections: "ABSTRACT" (50 token keywords) and "OVERVIEW" (500 token structured summary)
- **AND** the LLM response is parsed to extract both tiers
- **AND** if parsing fails, falls back to using the full response as L1 and first sentence as L0
