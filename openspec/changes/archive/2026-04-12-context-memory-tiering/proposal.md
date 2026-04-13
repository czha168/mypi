## Why

codepi's current context management uses a single-level compaction strategy: when token usage exceeds 80% of the context window, the entire conversation is summarized into a flat paragraph stored as a `compaction` entry. This loses granularity — individual decisions, file-specific knowledge, and recurring patterns get flattened into a single blob. There is no mechanism to extract reusable knowledge from sessions, no way to rank context by relevance, and no protection against memory bloat when patterns repeat across sessions.

Inspired by OpenViking's L0/L1/L2 tiering model, we can transform this flat compaction into a structured, tiered memory system that preserves knowledge at multiple granularities and makes context retrieval relevance-aware.

## What Changes

- **Three-tier compaction summaries**: Replace the single flat summary with L0 (~50 tokens, keyword/topic index), L1 (~500 tokens, structured overview), and L2 (full conversation) tiers generated during compaction
- **Bottom-up summarization**: Generate summaries from leaf messages upward through the session tree, preserving hierarchical context quality
- **Memory extraction pipeline**: After session compaction, extract reusable knowledge items (patterns, decisions, file associations) from the compacted session and persist them across sessions
- **Memory deduplication**: When extracting memories, compare against existing memories using content fingerprinting to prevent bloat (skip/create/merge/delete decisions)
- **Hotness scoring**: Track access frequency and recency for extracted memories, using a sigmoid + time-decay formula to boost frequently-used context during retrieval
- **Dual-layer storage**: Separate session JSONL files (conversation data) from a lightweight memory index (JSON-based, no vector DB required) for fast cross-session retrieval
- **Memory injection into system prompt**: Add a new prompt component that injects relevant memories (filtered by hotness and topic relevance) into the system prompt at session start

## Capabilities

### New Capabilities
- `tiered-compaction`: Multi-level session compaction producing L0 (abstract), L1 (overview), and L2 (full) summaries with bottom-up generation
- `memory-extraction`: Pipeline for extracting structured knowledge items from session archives with 4-category taxonomy (decisions, patterns, file-knowledge, preferences)
- `memory-dedup`: Content-fingerprint-based deduplication with skip/create/merge/delete decisions to prevent memory bloat
- `memory-store`: Lightweight JSON-based cross-session memory storage with hotness scoring and relevance retrieval
- `memory-prompt-injection`: Prompt component that injects relevant memories into the system prompt based on topic matching and hotness ranking

### Modified Capabilities
<!-- No existing specs are being modified at the requirements level -->

## Impact

- **codepi/core/session_manager.py**: `build_context()` and `SessionEntry` will support new entry types (`tiered_compaction`, `memory`). Compaction path reconstruction uses L0/L1/L2 tiers instead of flat summary.
- **codepi/core/agent_session.py**: `_run_auto_compaction()` rewritten to produce three-tier summaries instead of one flat paragraph. New `_run_memory_extraction()` method added post-compaction.
- **codepi/core/events.py**: New events for memory lifecycle (`MemoryExtractEvent`, `MemoryDedupEvent`).
- **codepi/prompts/components/**: New `memory.py` component for memory injection into system prompt. Updated `composer.py` to include memory section.
- **codepi/core/**: New `memory_store.py` (storage backend), `memory_extractor.py` (extraction pipeline), `memory_dedup.py` (deduplication logic).
- **~/.codepi/memories/**: New directory for persisted memory index and memory items.
- **Config**: New `[memory]` section in `config.toml` for extraction categories, hotness parameters, and storage settings.
- **Backward compatible**: Existing sessions with flat `compaction` entries continue to work. Tiered compaction applies only to new compactions.
