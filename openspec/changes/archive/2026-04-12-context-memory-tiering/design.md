## Context

codepi currently stores sessions as JSONL trees (v3) with a flat compaction mechanism. When token usage exceeds 80% of the context window, `_run_auto_compaction()` asks the LLM to summarize the entire conversation into a single paragraph, stored as a `compaction` entry. Context reconstruction via `build_context()` replaces all prior messages with one system message containing this flat summary.

The session tree (`SessionEntry` with `id`/`parent_id`) already supports branching. The extension system provides lifecycle hooks (`on_before_agent_start`, `on_tool_result`, etc.) that can intercept and augment behavior. The prompt composition system (`PromptComposer`) builds system prompts from modular components (persona, tools, constraints, efficiency).

There is no cross-session memory, no structured knowledge extraction, and no relevance-based context retrieval.

## Goals / Non-Goals

**Goals:**
- Replace flat compaction summaries with structured L0/L1/L2 tiers (abstract ~50 tokens, overview ~500 tokens, full conversation)
- Extract reusable knowledge from sessions into a persistent memory store with deduplication
- Score memories by hotness (frequency + recency) to prioritize relevant context
- Inject relevant memories into the system prompt at session start
- Maintain full backward compatibility with existing sessions

**Non-Goals:**
- Vector database or embedding-based semantic search (too heavy for a minimalist agent)
- Multi-tenancy or access control on memories
- Automatic hierarchical directory summarization (OpenViking's filesystem paradigm)
- Subagent-specific memory partitioning
- Memory editing UI or manual memory management

## Decisions

### D1: Three-tier compaction via two sequential LLM calls

**Decision**: Generate L0 and L1 in a single LLM call with structured output, then store L2 (original messages) in the session file. The compaction entry stores `{l0: "...", l1: "...", summary: "..."}` where `summary` is L1 for backward compat.

**Alternatives considered**:
- *Three separate LLM calls (L2→L1→L0)*: More tokens, slower, diminishing returns for a minimalist agent.
- *Single flat summary (status quo)*: Loses granularity, no tiered retrieval possible.
- *AST-based extraction for code files*: OpenViking supports tree-sitter extraction, but codepi conversations are mixed text/code, not pure codebases. Not worth the dependency.

**Rationale**: One structured LLM call produces both tiers cheaply. L0 is just a compressed version of L1 (extract keywords/topics). The `summary` field preserves backward compatibility — old code reading `compaction` entries still works.

### D2: JSON-based memory store with content fingerprints for dedup

**Decision**: Store memories as individual JSON files under `~/.codepi/memories/` with a `index.json` manifest. Dedup uses SHA-256 content hashing + keyword overlap scoring (no embeddings/vector DB).

**Alternatives considered**:
- *SQLite database*: More structured, but adds a dependency and complexity for what is essentially a few hundred memories.
- *FAISS/sentence-transformers*: Heavy dependencies, requires model download, overkill for a minimalist agent. OpenViking uses a C++ vector engine — not appropriate here.
- *Single JSON file*: Becomes unwieldy as memories grow. Per-item files allow atomic updates.

**Rationale**: A minimalist agent should have minimalist storage. SHA-256 dedup is deterministic and fast. Keyword overlap (Jaccard similarity on token sets) provides "good enough" semantic matching without ML dependencies. The manifest file (`index.json`) tracks hotness scores and metadata without scanning all files.

### D3: Hotness scoring with sigmoid + exponential decay

**Decision**: Use OpenViking's formula: `score = sigmoid(log1p(access_count)) * time_decay(updated_at)` where time_decay uses a 7-day half-life. Blend into retrieval ranking as 20% hotness + 80% topic relevance.

**Alternatives considered**:
- *Pure recency (LRU)*: Ignores frequently-accessed but older patterns.
- *Pure frequency*: Stale popular items dominate forever.
- *Learned relevance*: Requires training data and a model. Not viable for a tool that runs locally.

**Rationale**: The sigmoid + decay formula is battle-tested in OpenViking and provides a good balance. The 20/80 blend means topic relevance always dominates but frequently-used items get a meaningful boost.

### D4: Memory extraction as a post-compaction extension hook

**Decision**: Implement memory extraction as a built-in extension that hooks into `on_before_agent_start` (to inject memories) and runs extraction after auto-compaction completes. New events: `MemoryExtractEvent`, `MemoryDedupEvent`.

**Alternatives considered**:
- *Separate background process*: Complex IPC, no access to session state. Codepi is single-process.
- *Inline in `_run_auto_compaction`*: Couples memory logic to session logic. Extension approach keeps concerns separated and allows users to disable/replace memory behavior.
- *Post-session script*: No access to in-memory session state, would need to reparse JSONL.

**Rationale**: The extension system already provides the right hooks. `on_before_agent_start` can inject memories into the system prompt. A post-compaction callback can trigger extraction. Users can disable memory by removing the extension.

### D5: Four-category memory taxonomy

**Decision**: Extract memories into four categories: `decisions` (architectural choices, "use X not Y"), `patterns` (recurring code patterns, idioms), `file-knowledge` (project-specific file/function mappings), `preferences` (user's stated preferences).

**Alternatives considered**:
- *OpenViking's six categories* (profile, preferences, entities, events, cases, patterns): More granular but designed for multi-user SaaS. codepi is single-user.
- *Flat tag-based*: Loses the structure that makes retrieval and display cleaner.
- *Single type*: Too lossy.

**Rationale**: Four categories cover the meaningful distinctions for a coding assistant: what was decided, what patterns recur, what files exist, and what the user prefers. Simple enough to explain, structured enough to filter.

### D6: Bottom-up summarization within session tree

**Decision**: When compacting, walk the session tree from leaf to root. Each compaction entry summarizes only its subtree. When `build_context()` encounters a compaction entry, it uses L1 by default and falls back to L0 when token budget is tight.

**Alternatives considered**:
- *Top-down from root*: Loses leaf-level detail where actual work happens.
- *Flat summarization (status quo)*: No hierarchy, loses branch-specific context.
- *Full bottom-up with directory summarization*: Overkill for session trees which are linear chains with occasional branches.

**Rationale**: Sessions are mostly linear (one active leaf). Bottom-up within the active path gives the most relevant summary near the leaf. L0/L1/L2 at each compaction point allows the context builder to choose the right tier based on available token budget.

## Risks / Trade-offs

**[Extra LLM call during compaction]** → Mitigation: Generate L0+L1 in one structured call. The cost is ~500 extra output tokens per compaction. Compaction is already an LLM call, so this is marginal.

**[Memory bloat over time]** → Mitigation: Dedup with SHA-256 fingerprinting prevents identical memories. Hotness scoring naturally deprioritizes stale memories. Cap total memories at a configurable limit (default 500) with LRU eviction of lowest-hotness items.

**[Keyword-based dedup misses semantic duplicates]** → Mitigation: Add Jaccard similarity on token sets as a secondary check. Accept that some near-duplicates may slip through — this is acceptable for a minimalist agent. Can upgrade to embedding-based dedup later without architecture changes.

**[Backward compatibility with flat compaction]** → Mitigation: New `tiered_compaction` entry type alongside existing `compaction`. `build_context()` handles both: tiered entries use L0/L1/L2, flat entries work as before. Migration is lazy — old entries aren't rewritten.

**[Memory injection bloats system prompt]** → Mitigation: Cap injected memories at 1000 tokens. Use L0 abstracts (50 tokens each) for injection, not full L1. Only inject top-k by hotness × relevance. Budget is configurable.

**[Disk I/O for memory store]** → Mitigation: `index.json` is loaded once at session start and cached in memory. Individual memory files are only read on cache miss. For 500 memories, the index is <50KB.
