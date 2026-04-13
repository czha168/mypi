# OpenViking: Technical Deep Dive — Context Management Architecture

> **Source**: `openviking/` directory within the `mypi` project.
> **Origin**: [github.com/volcengine/OpenViking](https://github.com/volcengine/OpenViking) by Beijing Volcano Engine Technology (ByteDance).
> **License**: Apache 2.0

---

## 1. Executive Summary

OpenViking is an **open-source context database** purpose-built for AI Agents. It addresses five key challenges in Agent development:

1. **Fragmented context** — Memories, resources, and skills scattered across tools
2. **Surging context demand** — Agents produce context at every execution step
3. **Poor retrieval effectiveness** — Flat vector storage lacks hierarchical understanding
4. **Unobservable context** — Black-box RAG pipelines are hard to debug
5. **Limited memory iteration** — No task-level memory, only interaction logs

The solution rests on a **filesystem paradigm** for context management with a **three-tier information model (L0/L1/L2)**, **hierarchical directory-recursive retrieval**, and **automatic session-to-memory extraction**. This report provides a comprehensive technical analysis of how these systems work, with a particular focus on tiered storage for context management.

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        OpenViking System Architecture                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│                              ┌─────────────┐                            │
│                              │   Client    │                            │
│                              │ (Python/Rust│                            │
│                              │    /HTTP)   │                            │
│                              └──────┬──────┘                            │
│                                     │ delegates                         │
│                              ┌──────▼──────┐                            │
│                              │   Service   │                            │
│                              │    Layer    │                            │
│                              └──────┬──────┘                            │
│           ┌─────────────────────────┼──────────────────────┐            │
│           │                         │                      │            │
│           ▼                         ▼                      ▼            │
│    ┌─────────────┐          ┌─────────────┐        ┌─────────────┐     │
│    │  Retrieve   │          │   Session   │        │    Parse    │     │
│    │  (Intent    │          │  (Messages, │        │  (Document  │     │
│    │   Analysis  │          │   Compress, │        │   Parsing,  │     │
│    │   Hierarch. │          │   Memory    │        │   Tree      │     │
│    │   Rerank)   │          │   Extract)  │        │   Building) │     │
│    └──────┬──────┘          └──────┬──────┘        └──────┬──────┘     │
│           │                        │                       │            │
│           └────────────────────────┼───────────────────────┘            │
│                                    ▼                                     │
│    ┌────────────────────────────────────────────────────────────────┐   │
│    │                      Storage Layer                             │   │
│    │          AGFS (File Content)  +  Vector Index (C++)            │   │
│    └────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### Core Modules

| Module | Location | Responsibility |
|--------|----------|----------------|
| **Client** | `openviking/client/`, `openviking_cli/` | Unified entry point (Python sync/async, Rust CLI) |
| **Service** | `openviking/service/` | Business logic (FS, Search, Session, Resource, Relation) |
| **Retrieve** | `openviking/retrieve/` | Intent analysis, hierarchical retrieval, rerank |
| **Session** | `openviking/session/` | Message recording, compression, memory extraction |
| **Parse** | `openviking/parse/` | Document parsing (PDF/MD/HTML/Code), AST extraction |
| **Storage** | `openviking/storage/` | VikingFS virtual filesystem, vector index, AGFS |
| **C++ Engine** | `src/index/`, `src/store/` | High-performance vector search, KV storage, scalar indexing |

### Technology Stack

| Layer | Technology |
|-------|-----------|
| **Client/SDK** | Python 3.10+, Rust (CLI) |
| **Server** | Python HTTP (FastAPI-like), AGFS (Go subprocess) |
| **C++ Core** | C++17, pybind11/ABI3 bindings |
| **Vector Engine** | Custom flat hybrid index with SIMD (AVX512/AVX/SSE/NEON) |
| **Persistent KV** | LevelDB (via `PersistStore`) |
| **In-Memory KV** | `std::map` with `shared_mutex` (via `VolatileStore`) |
| **Sparse Vectors** | Custom CSR-based sparse row index |
| **Bitmap Index** | Roaring bitmaps for scalar filtering |

---

## 3. The Three-Tier Information Model (L0/L1/L2)

This is the **core innovation** of OpenViking's context management. All context data is automatically processed into three tiers upon ingestion.

### 3.1 Tier Definitions

| Tier | Name | File | Token Budget | Purpose |
|------|------|------|-------------|---------|
| **L0** | Abstract | `.abstract.md` | ~100 tokens | Vector search indexing, quick relevance filtering |
| **L1** | Overview | `.overview.md` | ~1–2k tokens | Rerank scoring, Agent planning-phase decision making |
| **L2** | Detail | Original files | Unlimited | Full content, loaded only when absolutely necessary |

### 3.2 Directory Structure

Every directory in the virtual filesystem follows this pattern:

```
viking://resources/docs/auth/
├── .abstract.md          # L0: ~100 tokens, used for vector search
├── .overview.md          # L1: ~1–2k tokens, used for rerank/planning
├── .relations.json       # Cross-resource link table
├── oauth.md              # L2: Full original content
├── jwt.md                # L2: Full original content
└── api-keys.md           # L2: Full original content
```

### 3.3 Generation Mechanism

**Bottom-up generation**: Leaf nodes → Parent directories → Root.

```
Input File → Parser → TreeBuilder → AGFS (L2) → SemanticQueue → L0/L1
                                                         ↓
                                              Bottom-up: children first
```

1. **Parser**: Converts documents to structured files (no LLM calls)
2. **TreeBuilder**: Moves temp directory into AGFS, enqueues for semantic processing
3. **SemanticQueue**: Asynchronous LLM-powered generation:
   - Concurrent file summarization (max 10 concurrent)
   - Collect child directory abstracts
   - Generate `.overview.md` (L1) via LLM
   - Extract `.abstract.md` (L0) from overview
   - Vectorize all three tiers into the vector index

### 3.4 Code Skeleton Extraction (AST Mode)

For code files, OpenViking supports tree-sitter-based AST extraction as a lightweight alternative to LLM summarization:

| Mode | Behavior |
|------|----------|
| `ast` | Extract structural skeleton for files ≥100 lines, skip LLM (**default**) |
| `llm` | Always use LLM for summarization |
| `ast_llm` | Extract AST skeleton first, then pass as context to LLM |

Supported languages: Python, JavaScript/TypeScript, Rust, Go, Java, C/C++.

### 3.5 Multimodal Support

- **L0/L1**: Always text (Markdown) — even for images/video/audio
- **L2**: Can be any format (text, image, video, audio, binary)
- Binary content gets text descriptions at L0/L1 that summarize visual/audio content

---

## 4. Dual-Layer Storage Architecture

### 4.1 Overview

OpenViking uses a **dual-layer storage** model that separates content storage from index storage:

```
┌───────────────────────────────────────────┐
│       VikingFS (URI Abstraction Layer)     │
│   viking:// → /local/{account}/...        │
│   L0/L1 reads, Relations, Semantic Search  │
└─────────────┬──────────────┬──────────────┘
        ┌─────┴──────┐  ┌───┴───────────────┐
        │ Vector     │  │  AGFS             │
        │ Index      │  │  (Content Storage) │
        │ (C++)      │  │  POSIX FS ops     │
        │ URIs +     │  │  L0/L1/L2 files   │
        │ Vectors +  │  │  .relations.json  │
        │ Metadata   │  │  Multimedia       │
        └────────────┘  └──────────────────┘
```

| Layer | Responsibility | Content |
|-------|----------------|---------|
| **AGFS** | Content storage | L0/L1/L2 full content, multimedia, relations |
| **Vector Index** | Index storage | URIs, vectors, metadata (**no file content**) |

**Key design principle**: The vector index stores **only references and embeddings** — never file content. All content is read from AGFS. This keeps the vector index memory-efficient while enabling fast semantic search.

### 4.2 AGFS — Agent File System

AGFS provides POSIX-style file operations with multiple backend support:

| Backend | Description |
|---------|-------------|
| `localfs` | Local filesystem (default) |
| `s3fs` | S3-compatible object storage |
| `memory` | In-memory (testing) |

AGFS is a Go subprocess that provides the actual file storage. The Python `VikingFS` class wraps it with URI translation and semantic capabilities.

### 4.3 VikingFS — The URI Abstraction Layer

`VikingFS` (in `openviking/storage/viking_fs.py`) is the central facade that bridges virtual URIs to physical storage:

```python
class VikingFS:
    # AGFS basic commands (forwarded)
    async def read(uri)       → bytes
    async def write(uri, data) → str
    async def mkdir(uri)      → None
    async def rm(uri)         → Dict   # Also syncs vector index deletion
    async def mv(old, new)    → Dict   # Also syncs vector URI update

    # VikingFS specific capabilities
    async def abstract(uri)    → str    # Read L0 (.abstract.md)
    async def overview(uri)    → str    # Read L1 (.overview.md)
    async def find(query)      → FindResult    # Semantic search
    async def search(query)    → FindResult    # Intent-analyzed search
    async def link(from, uris) → None   # Create relation
    async def unlink(from, uri) → None  # Delete relation
```

**URI Mapping**: `viking://{scope}/{path}` → `/local/{account_id}/{scope}/{path}`

```
viking://resources/docs/auth  →  /local/acct_123/resources/docs/auth
viking://user/memories        →  /local/acct_123/user/memories
viking://agent/skills         →  /local/acct_123/agent/skills
```

### 4.4 Vector Index Sync

VikingFS automatically maintains consistency between AGFS and the vector index:

| Operation | Vector Sync Behavior |
|-----------|---------------------|
| `rm(uri)` | Recursively collects all URIs, deletes from vector store, then deletes from AGFS |
| `mv(old, new)` | Copies in AGFS, updates URIs in vector store (preserving embeddings), deletes source |

Both operations use a **path lock** mechanism (`LockContext`) to prevent concurrent semantic processing from causing inconsistencies.

---

## 5. C++ Storage Engine — Tiered KV Store

### 5.1 KVStore Interface

The C++ engine (`src/store/kv_store.h`) defines a clean abstract interface:

```cpp
class KVStore {
public:
    virtual int exec_op(const std::vector<StorageOp>& ops) = 0;
    virtual vector<string> get_data(const vector<string>& keys) = 0;
    virtual int put_data(const vector<string>& keys, const vector<string>& values) = 0;
    virtual int delete_data(const vector<string>& keys) = 0;
    virtual int clear_data() = 0;
    virtual vector<pair<string,string>> seek_range(const string& start, const string& end) = 0;
};
```

`StorageOp` (`common_structs.h`) provides a unified operation abstraction:

```cpp
struct StorageOp {
    enum OpType { PUT_OP = 0, DELETE_OP = 1 };
    OpType type;
    string key;
    string value;
};
```

### 5.2 VolatileStore — Hot Tier (In-Memory)

**File**: `src/store/volatile_store.h/.cpp`

```cpp
class VolatileStore : public KVStore {
private:
    std::map<std::string, std::string> data_;
    mutable std::shared_mutex mutex_;
};
```

| Aspect | Detail |
|--------|--------|
| **Storage** | `std::map<string, string>` — ordered in-memory map |
| **Thread safety** | `shared_mutex`: shared_lock for reads, unique_lock for writes |
| **Reads** | `get_data()` returns values aligned with input keys; missing keys return empty |
| **Writes** | `put_data()` batch-inserts under unique_lock |
| **Range scans** | `seek_range()` uses `lower_bound` for efficient range iteration |
| **Batch ops** | `exec_op()` applies PUT_OP/DELETE_OP sequentially under lock |
| **Use case** | Fast in-memory cache for hot vector/metadata data during index operations |

### 5.3 PersistStore — Cold Tier (LevelDB)

**File**: `src/store/persist_store.h/.cpp`

```cpp
class PersistStore : public KVStore {
private:
    leveldb::DB* db_ = nullptr;
};
```

| Aspect | Detail |
|--------|--------|
| **Storage** | LevelDB on-disk key-value database |
| **Initialization** | Creates directories, opens LevelDB with `create_if_missing=true` |
| **Thread safety** | LevelDB's internal concurrency; snapshot-based consistent reads |
| **Reads** | `get_data()` uses LevelDB snapshots for consistent multi-key reads |
| **Writes** | `put_data()` uses `WriteBatch` with `sync=true` for durability |
| **Deletes** | `delete_data()` uses `WriteBatch` with sync |
| **Range scans** | `seek_range()` uses LevelDB iterator for efficient prefix/range queries |
| **Batch ops** | `exec_op()` batches PUT/DELETE into single atomic WriteBatch |
| **Use case** | Durable storage for index metadata, serialized vector data, schema records |

### 5.4 BytesRow — Structured Serialization

**File**: `src/store/bytes_row.h/.cpp`

BytesRow provides a typed binary serialization framework for structured rows stored in the KV engine:

**Supported field types**:
- Primitives: `INT64`, `UINT64`, `FLOAT32`, `BOOLEAN`
- Variable: `STRING`, `BINARY`
- Lists: `LIST_INT64`, `LIST_STRING`, `LIST_FLOAT32`

**Binary layout**:
```
┌─────────────┬──────────────────────┬─────────────────────┐
│   Header    │    Fixed Region      │   Variable Region    │
│ field_count │ offsets + fixed vals │ strings, lists, bins │
└─────────────┴──────────────────────┴─────────────────────┘
```

- Fixed fields (int, float, bool) stored inline in fixed region
- Variable fields (string, binary, lists) store an offset in fixed region pointing to variable region
- Strings prefixed with `UINT16` length; binaries with `UINT32` length
- Lists store element count followed by per-element data

This enables efficient storage of structured context metadata (URI, vectors, timestamps, counts) as compact binary rows in either VolatileStore or PersistStore.

---

## 6. Vector Index Engine (C++)

### 6.1 IndexEngine

```cpp
class IndexEngine {
public:
    IndexEngine(const string& path_or_json);
    int add_data(const vector<AddDataRequest>& data_list);
    int delete_data(const vector<DeleteDataRequest>& data_list);
    SearchResult search(const SearchRequest& req);
    int64_t dump(const string& dir);
    StateResult get_state();
private:
    shared_ptr<IndexManager> impl_;
};
```

### 6.2 Index Strategy

OpenViking uses a **flat hybrid index** combining dense and sparse vectors:

```python
index_meta = {
    "IndexType": "flat_hybrid",   # Brute-force with hybrid search
    "Distance": "cosine",         # Cosine similarity
    "Quant": "int8",              # INT8 quantization for memory efficiency
}
```

### 6.3 Vector Subsystem Architecture

```
VectorIndexAdapter (abstract)
  └── BruteForceIndex
        └── BruteforceSearch
              ├── Dense vectors (quantized float32 or int8)
              ├── Sparse vectors (CSR-based SparseRowIndex)
              └── Bitmap filtering (from scalar index)
```

**Key components**:

| Component | File | Purpose |
|-----------|------|---------|
| `BruteForceIndex` | `detail/vector/vector_index_adapter.h` | Concrete vector index using brute-force search |
| `BruteforceSearch` | `detail/vector/common/bruteforce.h` | Search engine with quantization + optional sparse |
| `Quantizer` | `detail/vector/common/quantizer.h` | Factory for float32/int8 quantizers |
| `Int8Quantizer` | `detail/vector/common/quantization_int8.h` | INT8 quantization with scale/norm metadata |
| `L2Space` / `InnerProductSpace` | `detail/vector/common/space_*.h` | Distance metrics with SIMD backends |
| `SparseRowIndex` | `detail/vector/sparse_retrieval/sparse_row_index.h` | CSR sparse vector storage and retrieval |
| `SparseDataHolder` | `detail/vector/sparse_retrieval/sparse_data_holder.h` | Sparse-dense score combination via logits |

### 6.4 Distance Metrics with SIMD

The engine supports two distance metrics, each with SIMD-optimized paths:

| Metric | SIMD Backends | Use Case |
|--------|---------------|----------|
| **L2 (Euclidean)** | AVX512, AVX, SSE, NEON, scalar fallback | General similarity |
| **Inner Product** | AVX512, AVX, SSE, NEON, scalar fallback | Cosine similarity (with normalization) |
| **INT8 L2** | AVX512, AVX, SSE | Quantized search |
| **INT8 IP** | AVX512, AVX, SSE | Quantized cosine |

### 6.5 Sparse Retrieval

OpenViking supports **hybrid dense+sparse** vector search:

- **Dense vectors**: Traditional embedding vectors (e.g., 1024-dim from OpenAI/Volcengine)
- **Sparse vectors**: Term-weighted sparse representations (like SPLADE)
- **CSR format**: Compressed Sparse Row for efficient storage and dot-product computation
- **Score combination**: Dense and sparse scores combined via logit-based weighting

### 6.6 Scalar Indexing and Bitmap Filtering

The scalar index (`detail/scalar/`) provides bitmap-based filtering that integrates with vector search:

```
ScalarIndex
  └── FieldBitmapGroupSet
        ├── FieldBitmapGroup (per field)
        │     ├── BitmapGroup (string terms → roaring bitmaps)
        │     ├── RangedMap (numeric ranges → scored bitmaps)
        │     └── DirIndex (path-based prefix bitmaps)
        └── Filter DSL (AND/OR/Range/Contains/Prefix/Regex)
```

**Integration with vector search**: Scalar filter results produce a `Bitmap` that is passed to `BruteForceSearch::search_knn()`. The vector engine only computes distances for offsets matching the bitmap, enabling efficient pre-filtering.

### 6.7 Metadata Management

```
ManagerMeta
  ├── VectorIndexMeta (index type, dimension, distance, quantization, sparse config)
  │     └── BruteForceMeta
  ├── ScalarIndexMeta (field definitions, types)
  └── JSON serialization to/from disk
```

---

## 7. Python Vector Index Backend

### 7.1 VikingVectorIndexBackend

`openviking/storage/viking_vector_index_backend.py` provides the Python-side facade:

```python
class VikingVectorIndexBackend:
    """Singleton facade managing per-account backend instances."""

    ALLOWED_CONTEXT_TYPES = {"resource", "skill", "memory"}

    def __init__(self, config: VectorDBBackendConfig):
        self._shared_adapter = create_collection_adapter(config)
        self._account_backends: Dict[str, _SingleAccountBackend] = {}
```

**Key design**: A single shared C++ adapter (with its underlying PersistStore) is shared across all account backends to avoid RocksDB lock contention. Each account gets its own `_SingleAccountBackend` that enforces tenant isolation via `account_id` filters.

### 7.2 Context Collection Schema

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Primary key (MD5 hash of account+uri) |
| `uri` | string | Viking URI |
| `parent_uri` | string | Parent directory URI |
| `context_type` | string | `resource` / `memory` / `skill` |
| `level` | int | 0 (L0), 1 (L1), or 2 (L2) |
| `vector` | vector | Dense embedding |
| `sparse_vector` | sparse_vector | Sparse embedding |
| `abstract` | string | L0 abstract text |
| `name` | string | Entry name |
| `account_id` | string | Tenant isolation |
| `owner_space` | string | User/agent space |
| `active_count` | int64 | Usage count (for hotness scoring) |
| `updated_at` | string | Last update timestamp |

### 7.3 Tenant-Aware Search Methods

| Method | Purpose |
|--------|---------|
| `search_global_roots_in_tenant()` | Global vector search across all levels (0,1,2) |
| `search_children_in_tenant()` | Search children of a specific parent URI (depth=1) |
| `search_similar_memories()` | Find similar memories for deduplication |
| `get_context_by_uri()` | Fetch context records by URI prefix |
| `update_uri_mapping()` | Move operation: update URI + parent_uri, preserve embeddings |
| `increment_active_count()` | Track usage for hotness scoring |

---

## 8. Hierarchical Retrieval System

### 8.1 Two Search Modes

| Feature | `find()` | `search()` |
|---------|----------|------------|
| Session context | Not needed | Required |
| Intent analysis | Not used | LLM analyzes intent |
| Query count | Single query | 0–5 `TypedQuery`s |
| Latency | Low | Higher |
| Use case | Simple semantic queries | Complex multi-intent tasks |

### 8.2 Intent Analysis (for `search()`)

`IntentAnalyzer` uses an LLM to decompose a complex query into 0–5 typed queries:

```python
@dataclass
class TypedQuery:
    query: str              # Rewritten query
    context_type: ContextType  # MEMORY / RESOURCE / SKILL
    intent: str             # Query purpose
    priority: int           # 1-5 priority
    target_directories: List[str]  # Scope constraints
```

**Query styles by context type**:
- **skill**: Verb-first ("Create RFC document")
- **resource**: Noun phrase ("RFC document template")
- **memory**: Possessive ("User's code style preferences")

### 8.3 Directory Recursive Retrieval Algorithm

This is OpenViking's **key retrieval innovation**. The `HierarchicalRetriever` (in `openviking/retrieve/hierarchical_retriever.py`) implements a priority-queue-based recursive search:

```
Step 1: Determine root directories by context_type
        ↓
Step 2: Global vector search → locate high-score starting directories
        ↓
Step 3: Merge starting points + optional rerank scoring
        ↓
Step 4: Recursive search (priority queue, max-heap by score)
        ↓
Step 5: Convert to MatchedContext with hotness blending
```

**Core recursive search loop**:

```python
while dir_queue:
    current_uri, parent_score = heapq.heappop(dir_queue)

    # Search children of current directory
    results = await vector_proxy.search_children_in_tenant(
        parent_uri=current_uri, query_vector=query_vector, ...
    )

    for r in results:
        # Score propagation: blend embedding score with parent score
        final_score = alpha * embedding_score + (1 - alpha) * parent_score

        if final_score > threshold:
            collected_by_uri[uri] = r

            # Recurse into directories (L0/L1), not into L2 files
            if r.level != 2:
                heapq.heappush(dir_queue, (r.uri, final_score))

    # Convergence: stop if top-k unchanged for 3 rounds
    if topk_unchanged_for_3_rounds:
        break
```

### 8.4 Key Retrieval Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| `SCORE_PROPAGATION_ALPHA` | 0.5 | 50% embedding + 50% parent score |
| `MAX_CONVERGENCE_ROUNDS` | 3 | Stop if top-k unchanged for N rounds |
| `GLOBAL_SEARCH_TOPK` | 5 | Initial global search candidates |
| `MAX_RELATIONS` | 5 | Max related contexts per result |
| `HOTNESS_ALPHA` | 0.2 | Weight for hotness in final ranking |
| `DIRECTORY_DOMINANCE_RATIO` | 1.2 | Directory must exceed child score |

### 8.5 Rerank Strategy

When a rerank service is configured (e.g., Volcengine `doubao-seed-rerank`):

1. **Starting point evaluation**: Rerank global search candidate directories
2. **Recursive search**: Rerank children at each directory level
3. **Fallback**: If rerank fails or returns invalid results, fall back to raw vector scores

### 8.6 Hotness Scoring

`hotness_score()` (in `openviking/retrieve/memory_lifecycle.py`) blends frequency and recency:

```python
score = sigmoid(log1p(active_count)) * time_decay(updated_at)
```

- **Frequency**: `sigmoid(log1p(active_count))` maps access count to (0,1)
- **Recency**: Exponential decay with 7-day half-life
- **Blending**: `final = (1 - α) × semantic + α × hotness` where α = 0.2

---

## 9. Three Context Types

### 9.1 Resource

External knowledge added by users. Static, long-lived.

```
viking://resources/
├── my_project/
│   ├── docs/
│   ├── src/
│   └── README.md
```

### 9.2 Memory

Agent-learned knowledge extracted from sessions. Dynamic, personalized.

| Category | Location | Update Strategy |
|----------|----------|-----------------|
| **profile** | `user/memories/.overview.md` | Appendable |
| **preferences** | `user/memories/preferences/` | Appendable |
| **entities** | `user/memories/entities/` | Appendable |
| **events** | `user/memories/events/` | Immutable |
| **cases** | `agent/memories/cases/` | Immutable |
| **patterns** | `agent/memories/patterns/` | Appendable |

### 9.3 Skill

Callable capabilities (tool definitions, MCP integrations).

```
viking://agent/skills/{skill-name}/
├── .abstract.md     # L0: Short description
├── SKILL.md         # L1: Detailed overview
└── scripts          # L2: Full definition
```

---

## 10. Session Management and Memory Extraction

### 10.1 Session Lifecycle

```
Create → Interact (add_message, used) → Commit
```

**Two-phase commit**:

1. **Phase 1 (synchronous)**: Increment compression index, write messages to archive (`messages.jsonl`), clear current messages, return `task_id`
2. **Phase 2 (asynchronous background)**: Generate L0/L1 summaries via LLM, extract long-term memories, update `active_count`, write `.done` marker

### 10.2 Memory Extraction Pipeline

```
Messages → LLM Extract → Candidate Memories
              ↓
Vector Pre-filter → Find Similar Memories
              ↓
LLM Dedup Decision → (skip / create / merge / delete)
              ↓
Write to AGFS → Vectorize
```

**Dedup decisions** prevent memory bloat:

| Level | Decision | Description |
|-------|----------|-------------|
| Candidate | `skip` | Duplicate — do nothing |
| Candidate | `create` | New memory (optionally delete conflicting existing) |
| Per-existing | `merge` | Merge candidate content into existing memory |
| Per-existing | `delete` | Remove conflicting existing memory |

### 10.3 Session Storage Structure

```
viking://session/{session_id}/
├── messages.jsonl            # Current messages
├── .abstract.md              # Current abstract
├── .overview.md              # Current overview
├── history/
│   ├── archive_001/
│   │   ├── messages.jsonl
│   │   ├── .abstract.md
│   │   ├── .overview.md
│   │   └── .done
│   └── archive_NNN/
└── tools/
    └── {tool_id}/tool.json
```

---

## 11. Data Flow: End-to-End Traces

### 11.1 Adding a Resource

```
User adds URL/file
    ↓
Parser (format conversion, no LLM)
    ↓
TreeBuilder (move to AGFS, queue semantic)
    ↓
SemanticQueue (async bottom-up):
    ├── Concurrent file summarization (10 max)
    ├── Collect child abstracts
    ├── Generate .overview.md (LLM → L1)
    ├── Extract .abstract.md (from L1 → L0)
    ├── Write L0/L1 files to AGFS
    └── Vectorize all tiers → Vector Index
```

### 11.2 Retrieving Context

```
User query: "How to authenticate?"
    ↓
Intent Analysis (LLM) → TypedQuery(context_type=RESOURCE, ...)
    ↓
HierarchicalRetriever.retrieve():
    ├── Determine root URIs: viking://resources
    ├── Global vector search → locate top-5 directories
    ├── Merge starting points + rerank
    └── Recursive directory search:
        ├── Pop highest-scored directory from priority queue
        ├── Search children via vector index
        ├── Rerank children
        ├── Score propagation: 50% embedding + 50% parent
        ├── Collect passing candidates
        ├── Push subdirectories into queue
        └── Convergence check (3 rounds unchanged)
    ↓
Hotness blending: 80% semantic + 20% hotness
    ↓
Return FindResult(memories=[], resources=[...], skills=[])
```

### 11.3 Session Commit → Memory Extraction

```
session.commit()
    ↓
Phase 1 (sync):
    ├── Write messages to archive_XXX/messages.jsonl
    └── Return task_id
    ↓
Phase 2 (async background):
    ├── Generate L0/L1 for archived history
    ├── Extract 6-category memories via LLM
    ├── Vector search for similar existing memories
    ├── LLM dedup decision (skip/create/merge/delete)
    ├── Write final memories to AGFS
    └── Vectorize new memories
```

---

## 12. Performance Benchmarks (from README)

Testing against LoCoMo10 long-range dialogues (1,540 cases):

| Experimental Group | Task Completion | Input Tokens |
|----------|------------|------------|
| OpenClaw (memory-core) | 35.65% | 24,611,530 |
| OpenClaw + LanceDB (-memory-core) | 44.55% | 51,574,530 |
| **OpenClaw + OpenViking (-memory-core)** | **52.08%** | **4,264,396** |
| **OpenClaw + OpenViking (+memory-core)** | **51.23%** | **2,099,622** |

**Key results**: 43–49% improvement in task completion with 83–96% reduction in token cost compared to baselines.

---

## 13. Multi-Tenancy and Security

### 13.1 Tenant Isolation

Every vector store query enforces `account_id` filtering:

```python
class _SingleAccountBackend:
    async def query(self, ...):
        if self._bound_account_id:
            account_filter = Eq("account_id", self._bound_account_id)
            filter = And([account_filter, filter])
```

### 13.2 URI Access Control

```python
class VikingFS:
    def _is_accessible(self, uri, ctx):
        if ctx.role == Role.ROOT: return True
        if scope in {"resources", "temp"}: return True
        if scope in {"user", "session"}:
            return space == ctx.user.user_space_name()
        if scope == "agent":
            return space == ctx.user.agent_space_name()
```

### 13.3 Encryption

VikingFS supports optional file-level encryption via a `FileEncryptor`:
- Files are encrypted on write and decrypted on read
- Account-scoped encryption keys
- Transparent to callers — encryption happens inside `write()`/`read()`

---

## 14. Build and Deployment

### 14.1 Build System

| Component | Build Tool | Output |
|-----------|-----------|--------|
| C++ Engine | CMake + pybind11 | `_abi3_engine` native extension |
| Python SDK | pip / uv | `openviking` package |
| Rust CLI | Cargo | `ov` binary |
| AGFS (Go) | Go build | `agfs` subprocess |

### 14.2 Deployment Modes

| Mode | Description |
|------|-------------|
| **Embedded** | `client = OpenViking(path="./data")` — auto-starts AGFS subprocess |
| **HTTP Server** | `openviking-server` — standalone HTTP service on port 1933 |
| **Docker** | `docker-compose.yml` provided for containerized deployment |

---

## 15. Key Takeaways for Context Management Design

### What Makes OpenViking's Approach Effective

1. **L0/L1/L2 tiering** eliminates the "all-or-nothing" context injection problem. Agents can quickly scan L0 abstracts (~100 tokens) to identify relevant contexts, read L1 overviews (~2k tokens) for planning, and only load L2 full content when deep information is needed.

2. **Filesystem paradigm** provides deterministic, traceable context management. Unlike black-box RAG, every context has a unique URI that can be browsed (`ls`), searched (`find`), and traced.

3. **Directory recursive retrieval** combines the strengths of hierarchical organization and semantic search. Instead of flat vector search across all chunks, it first locates high-score directories, then drills down into children, with score propagation ensuring contextually coherent results.

4. **Automatic memory lifecycle** — Sessions are compressed, archived, and memories extracted automatically. The 6-category memory taxonomy (profile, preferences, entities, events, cases, patterns) provides structured self-improvement.

5. **Dual-layer storage** separates content (AGFS) from index (vector engine), enabling independent scaling and keeping the vector index memory-efficient (stores only URIs + embeddings, not file content).

6. **Tenant isolation** is enforced at every layer — URI access control in VikingFS, `account_id` filtering in vector queries, and optional file-level encryption.

### Lessons for mypi Implementation

OpenViking's architecture offers several patterns directly applicable to a minimalist coding agent:

| OpenViking Pattern | Applicable to mypi |
|--------------------|--------------------|
| L0/L1/L2 tiering | Session compaction summaries could use a similar 3-tier model |
| Filesystem paradigm | Tree-structured JSONL sessions already follow this concept |
| Bottom-up summarization | Context summaries generated from leaf messages upward |
| Memory extraction pipeline | Could extract patterns/cases from session archives |
| Dual-layer storage | Separate session files (JSONL) from search indices |
| Hotness scoring | Track which contexts are frequently used for relevance boosting |
| Dedup decisions | Prevent memory bloat when extracting patterns |

---

## Appendix A: File Index

### C++ Source (`src/`)

| Path | Role |
|------|------|
| `store/kv_store.h` | Abstract KVStore interface |
| `store/volatile_store.h/.cpp` | In-memory hot store (`std::map` + `shared_mutex`) |
| `store/persist_store.h/.cpp` | LevelDB-backed cold store |
| `store/bytes_row.h/.cpp` | Structured binary serialization (Schema + BytesRow) |
| `store/common_structs.h` | StorageOp operation type |
| `index/index_engine.h/.cpp` | Top-level IndexEngine facade |
| `index/index_manager.h` | IndexManager interface |
| `index/detail/index_manager_impl.h/.cpp` | Concrete IndexManager implementation |
| `index/detail/vector/vector_index_adapter.h` | BruteForceIndex adapter |
| `index/detail/vector/common/bruteforce.h` | Brute-force search with quantization |
| `index/detail/vector/common/quantizer.h` | Float32/INT8 quantizer factory |
| `index/detail/vector/common/space_*.h` | L2/IP distance metrics with SIMD |
| `index/detail/vector/sparse_retrieval/` | CSR sparse vector index |
| `index/detail/scalar/` | Bitmap-based scalar filtering |
| `index/detail/meta/` | Index metadata management |

### Python Source (`openviking/`)

| Path | Role |
|------|------|
| `storage/viking_fs.py` | VikingFS URI abstraction layer |
| `storage/viking_vector_index_backend.py` | Python vector index facade with multi-tenancy |
| `storage/vectordb/` | C++ engine Python bindings |
| `retrieve/hierarchical_retriever.py` | Directory recursive retrieval algorithm |
| `retrieve/intent_analyzer.py` | LLM-based intent analysis |
| `retrieve/memory_lifecycle.py` | Hotness scoring for context ranking |
| `session/session.py` | Session lifecycle management |
| `session/compressor.py` | Message compression and archiving |
| `session/memory_extractor.py` | 6-category memory extraction |
| `session/memory_deduplicator.py` | Memory deduplication via vector search + LLM |
| `parse/` | Document parsing pipeline |
| `service/` | Business logic layer |
| `server/` | HTTP server |

### Documentation (`docs/en/concepts/`)

| Document | Content |
|----------|---------|
| `01-architecture.md` | System architecture overview |
| `02-context-types.md` | Resource/Memory/Skill types |
| `03-context-layers.md` | L0/L1/L2 tier model |
| `04-viking-uri.md` | URI specification |
| `05-storage.md` | Dual-layer storage details |
| `06-extraction.md` | Parsing and extraction pipeline |
| `07-retrieval.md` | Retrieval mechanism |
| `08-session.md` | Session management |
