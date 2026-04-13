## ADDED Requirements

### Requirement: Memory section in system prompt
The prompt composer SHALL include a "Relevant Memories" section in the system prompt when memories are available.

#### Scenario: Memories injected into system prompt
- **WHEN** a new session starts or a new prompt is submitted
- **AND** the memory store contains memories matching the current prompt's topic keywords
- **THEN** the system prompt includes a section titled "## Relevant Memories from Past Sessions"
- **AND** each included memory is formatted as: `[{category}] {content}`
- **AND** the total memory section does not exceed a configurable token budget (default: 1000 tokens)

#### Scenario: No relevant memories
- **WHEN** the memory store is empty or no memories match the current topic keywords
- **THEN** no memory section is added to the system prompt
- **AND** the prompt composition proceeds normally without error

### Requirement: Topic keyword extraction from prompt
The system SHALL extract topic keywords from the user's prompt text for memory matching.

#### Scenario: Keyword extraction from user message
- **WHEN** the user submits a prompt
- **THEN** the system extracts keywords by tokenizing the prompt and filtering to significant words (length > 3, not common stopwords)
- **AND** extracted keywords are used to query the memory store for matching memories

#### Scenario: Multi-turn conversation context
- **WHEN** the conversation has prior messages in the current context
- **THEN** topic keywords are extracted from the last 3 user messages (or fewer if not available)
- **AND** keywords are deduplicated before querying

### Requirement: Memory injection via BeforeAgentStartEvent
The memory injection SHALL be implemented as a built-in extension hooking into `on_before_agent_start`.

#### Scenario: Extension modifies system prompt with memories
- **WHEN** the `BeforeAgentStartEvent` is dispatched
- **THEN** the memory extension retrieves relevant memories based on the event's messages
- **AND** appends the memory section to `event.system_prompt`
- **AND** returns the modified event

#### Scenario: Extension handles memory store errors gracefully
- **WHEN** the memory store is unavailable (corrupted index, permission error)
- **THEN** the extension logs a warning and returns the event unmodified
- **AND** the agent session continues normally without memories

### Requirement: Hotness-weighted memory ranking in injection
Memories injected into the prompt SHALL be ranked by a blended score of topic relevance and hotness.

#### Scenario: Blended ranking
- **WHEN** multiple memories match the topic keywords
- **THEN** each memory's final score is: `0.8 * topic_overlap_ratio + 0.2 * hotness_score`
- **AND** `topic_overlap_ratio` is the fraction of the memory's topics that match the query keywords
- **AND** memories are included in the prompt in descending score order until the token budget is exhausted
