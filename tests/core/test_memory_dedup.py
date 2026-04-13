from codepi.core.memory_dedup import (
    DedupDecision, MemoryDeduplicator, compute_content_hash, compute_jaccard_similarity,
)
from codepi.core.memory_store import MemoryCategory, MemoryItem, MemoryStore


class TestComputeContentHash:
    def test_normalized_hash(self):
        h1 = compute_content_hash("Hello World")
        h2 = compute_content_hash("hello   world")
        assert h1 == h2

    def test_different_content(self):
        h1 = compute_content_hash("foo")
        h2 = compute_content_hash("bar")
        assert h1 != h2


class TestComputeJaccardSimilarity:
    def test_identical(self):
        assert compute_jaccard_similarity("the cat sat", "the cat sat") == 1.0

    def test_no_overlap(self):
        assert compute_jaccard_similarity("aaa bbb", "ccc ddd") == 0.0

    def test_partial_overlap(self):
        sim = compute_jaccard_similarity("the cat sat", "the dog sat")
        assert 0.0 < sim < 1.0

    def test_empty(self):
        assert compute_jaccard_similarity("", "") == 0.0


class TestMemoryDeduplicator:
    def test_exact_dup_skip(self, tmp_path):
        store = MemoryStore(store_dir=tmp_path / "memories")
        existing = MemoryItem(content="Use SQLite for storage", category=MemoryCategory.decisions, topics=["sqlite"])
        store.add(existing)
        dedup = MemoryDeduplicator()
        dedup.index_existing(store)

        candidate = MemoryItem(content="Use SQLite for storage", category=MemoryCategory.decisions, topics=["sqlite"])
        result = dedup.check(candidate, store)
        assert result.decision == DedupDecision.skip

    def test_high_jaccard_merge(self, tmp_path):
        store = MemoryStore(store_dir=tmp_path / "memories")
        existing = MemoryItem(
            content="Always use type hints in all Python functions and methods throughout the codebase",
            category=MemoryCategory.preferences, topics=["python", "types"],
        )
        store.add(existing)
        dedup = MemoryDeduplicator(jaccard_threshold=0.5)
        dedup.index_existing(store)

        candidate = MemoryItem(
            content="Always use type hints in all Python functions and methods throughout the codebase consistently",
            category=MemoryCategory.preferences, topics=["python", "types"],
        )
        result = dedup.check(candidate, store)
        assert result.decision == DedupDecision.merge

    def test_low_jaccard_create(self, tmp_path):
        store = MemoryStore(store_dir=tmp_path / "memories")
        existing = MemoryItem(
            content="Use pytest for testing framework", category=MemoryCategory.preferences, topics=["testing"],
        )
        store.add(existing)
        dedup = MemoryDeduplicator()
        dedup.index_existing(store)

        candidate = MemoryItem(
            content="Database schema migration uses Alembic", category=MemoryCategory.decisions, topics=["database"],
        )
        result = dedup.check(candidate, store)
        assert result.decision == DedupDecision.create
