## 1. Memory Store Foundation

- [x] 1.1 Create `codepi/core/memory_store.py` with `MemoryItem` dataclass (id, content, category, topics, source_session_id, created_at, updated_at, access_count, hotness_score) and `MemoryCategory` enum (decisions, patterns, file_knowledge, preferences)
- [x] 1.2 Implement `MemoryStore` class with `__init__(store_dir: Path)` that initializes `~/.codepi/memories/` directory structure (items/ subdirectory, index.json manifest)
- [x] 1.3 Implement `MemoryStore.add(item: MemoryItem)` — write JSON file to items/, update index.json atomically (write temp → rename)
- [x] 1.4 Implement `MemoryStore.get(item_id: str) -> MemoryItem` — read from items/{hash_prefix}.json
- [x] 1.5 Implement `MemoryStore.update(item_id: str, **fields)` — update fields, recalculate hotness, rewrite file and index
- [x] 1.6 Implement `MemoryStore.delete(item_id: str)` — remove file and index entry
- [x] 1.7 Implement `MemoryStore.retrieve_by_topics(keywords: list[str], limit: int = 20) -> list[MemoryItem]` — filter index.json by topic overlap, sort by hotness_score desc
- [x] 1.8 Implement `compute_hotness(access_count: int, updated_at: str) -> float` — sigmoid(log1p(count)) * time_decay(updated_at) with 7-day half-life
- [x] 1.9 Implement `MemoryStore.enforce_capacity(max_items: int = 500)` — evict lowest-hotness items (excluding preferences category), delete files and update index
- [x] 1.10 Add `[memory]` config section to `codepi/config.py` with: enabled (bool), max_items (int), injection_token_budget (int), hotness_half_life_days (int), dedup_jaccard_threshold (float)

## 2. Memory Deduplication

- [x] 2.1 Create `codepi/core/memory_dedup.py` with `DedupDecision` enum (skip, create, merge) and `DedupResult` dataclass (decision, matched_id, similarity_score)
- [x] 2.2 Implement `compute_content_hash(content: str) -> str` — normalize whitespace, lowercase, SHA-256
- [x] 2.3 Implement `compute_jaccard_similarity(text_a: str, text_b: str) -> float` — tokenize, compute set intersection/union ratio
- [x] 2.4 Implement `MemoryDeduplicator.check(candidate: MemoryItem, store: MemoryStore) -> DedupResult` — check content hash for exact dup, then Jaccard for semantic dup (>0.7 = merge, >0.4 = create with related link, <0.4 = create)
- [x] 2.5 Implement `MemoryDeduplicator.merge_content(existing: str, candidate: str) -> str` — keep longer/more detailed version
- [x] 2.6 Add `MemoryDedupEvent` to `codepi/core/events.py` (candidate_hash, matched_hash, similarity_score, decision, category)

## 3. Memory Extraction Pipeline

- [x] 3.1 Create `codepi/core/memory_extractor.py` with `MemoryExtractor` class
- [x] 3.2 Implement extraction prompt template: structured LLM call requesting JSON array of extracted items with {category, content, topics} from L1 overview
- [x] 3.3 Implement `MemoryExtractor.extract(l1_overview: str, session_id: str, provider: LLMProvider, model: str) -> list[MemoryItem]` — send prompt, parse JSON response, handle malformed responses gracefully (log warning, return empty)
- [x] 3.4 Implement `MemoryExtractor.extract_from_messages(messages: list[dict], session_id: str, provider: LLMProvider, model: str) -> list[MemoryItem]` — fallback extraction from raw messages when L1 is insufficient
- [x] 3.5 Implement keyword extraction helper `extract_topics(text: str) -> list[str]` — tokenize, filter stopwords, keep significant words (length > 3)
- [x] 3.6 Add `MemoryExtractEvent` to `codepi/core/events.py` (session_id, items_extracted, categories_breakdown)

## 4. Tiered Compaction

- [x] 4.1 Add `tiered_compaction` entry type support to `SessionEntry` — data contains {l0, l1, summary} where summary = l1 for backward compat
- [x] 4.2 Create tiered compaction prompt template: single LLM call requesting structured output with "ABSTRACT" (50 tokens) and "OVERVIEW" (500 tokens) sections
- [x] 4.3 Implement `parse_tiered_response(raw: str) -> tuple[str, str]` — extract L0 and L1 from structured response, fallback to full=L1, first_sentence=L0
- [x] 4.4 Rewrite `_run_auto_compaction()` in `agent_session.py` to use tiered compaction — generate L0+L1, store as `tiered_compaction` entry
- [x] 4.5 Update `build_context()` in `session_manager.py` to handle `tiered_compaction` entries — use L1 when budget > 2000 tokens, L0 when budget < 500 tokens
- [x] 4.6 Verify backward compat: `build_context()` still handles old `compaction` entries by treating `summary` as L1 and truncating to L0

## 5. Memory Injection via Extension

- [x] 5.1 Create `codepi/extensions/memory_extension.py` with `MemoryExtension(Extension)` class
- [x] 5.2 Implement `MemoryExtension.on_before_agent_start(event) -> BeforeAgentStartEvent` — extract keywords from last 3 user messages, query MemoryStore, format as "## Relevant Memories from Past Sessions" section, append to system_prompt
- [x] 5.3 Implement memory formatting: `format_memories_for_prompt(items: list[MemoryItem], token_budget: int) -> str` — `[category] content` format, sorted by blended score (0.8 * topic_overlap + 0.2 * hotness), truncated to budget
- [x] 5.4 Implement graceful error handling — if memory store unavailable, log warning and return event unmodified
- [x] 5.5 Add memory prompt component to `codepi/prompts/components/memory.py` with `MEMORY_SECTION_HEADER` constant
- [x] 5.6 Register `MemoryExtension` as built-in extension in agent initialization (when `[memory] enabled = true` in config)

## 6. Post-Compaction Memory Extraction Hook

- [x] 6.1 Add post-compaction callback in `agent_session.py` — after `_run_auto_compaction()` completes, call `_run_memory_extraction()` if memory is enabled
- [x] 6.2 Implement `_run_memory_extraction(l1_overview: str)` — call MemoryExtractor.extract(), then run each candidate through MemoryDeduplicator, store surviving items via MemoryStore
- [x] 6.3 Wire `MemoryExtractEvent` and `MemoryDedupEvent` into extension dispatch (same pattern as existing events)

## 7. Configuration and Integration

- [x] 7.1 Add `[memory]` section to default config in `codepi/config.py` with sensible defaults (enabled=true, max_items=500, injection_budget=1000, hotness_half_life=7, dedup_threshold=0.7)
- [x] 7.2 Update `README.md` with memory system documentation — config options, how it works, disabling
- [x] 7.3 Wire MemoryExtension into interactive mode initialization in `codepi/modes/interactive.py`
- [x] 7.4 Wire MemoryExtension into print mode and SDK mode initialization

## 8. Tests

- [x] 8.1 Unit tests for `compute_hotness()` — verify sigmoid(0)=0.5, time_decay(7d)=0.5, fresh high-access ≈0.95, old popular decays correctly
- [x] 8.2 Unit tests for `MemoryStore` — add, get, update, delete, retrieve_by_topics, enforce_capacity with eviction
- [x] 8.3 Unit tests for `MemoryDeduplicator` — exact dup → skip, high Jaccard → merge, low Jaccard → create
- [x] 8.4 Unit tests for `parse_tiered_response()` — valid structured output, malformed output fallback
- [x] 8.5 Unit tests for `build_context()` with tiered_compaction entries — L1 used when budget sufficient, L0 used when tight
- [x] 8.6 Unit tests for `build_context()` with old compaction entries — backward compatibility preserved
- [x] 8.7 Integration test: full compaction → extraction → dedup → store → retrieval → injection pipeline
