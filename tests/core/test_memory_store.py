import math
from datetime import datetime, timezone, timedelta

from codepi.core.memory_store import compute_hotness, MemoryCategory, MemoryItem, MemoryStore


class TestComputeHotness:
    def test_sigmoid_zero(self):
        assert abs(compute_hotness(0, "") - 0.5) < 0.01

    def test_time_decay_seven_days(self):
        seven_days_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        score = compute_hotness(0, seven_days_ago)
        assert abs(score - 0.25) < 0.01

    def test_fresh_high_access(self):
        now = datetime.now(timezone.utc).isoformat()
        score = compute_hotness(20, now)
        assert score > 0.9

    def test_old_popular_decays(self):
        fourteen_days_ago = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()
        score = compute_hotness(50, fourteen_days_ago)
        assert score < 0.5

    def test_zero_count_now(self):
        now = datetime.now(timezone.utc).isoformat()
        score = compute_hotness(0, now)
        assert abs(score - 0.5) < 0.01


class TestMemoryStore:
    def test_add_and_get(self, tmp_path):
        store = MemoryStore(store_dir=tmp_path / "memories")
        item = MemoryItem(
            content="Test content",
            category=MemoryCategory.decisions,
            topics=["test"],
            source_session_id="sess1",
        )
        store.add(item)
        retrieved = store.get(item.id)
        assert retrieved is not None
        assert retrieved.content == "Test content"
        assert retrieved.category == MemoryCategory.decisions

    def test_update(self, tmp_path):
        store = MemoryStore(store_dir=tmp_path / "memories")
        item = MemoryItem(content="original", category=MemoryCategory.patterns, topics=["x"])
        store.add(item)
        store.update(item.id, content="updated")
        retrieved = store.get(item.id)
        assert retrieved is not None
        assert retrieved.content == "updated"

    def test_delete(self, tmp_path):
        store = MemoryStore(store_dir=tmp_path / "memories")
        item = MemoryItem(content="to delete", category=MemoryCategory.patterns, topics=[])
        store.add(item)
        store.delete(item.id)
        assert store.get(item.id) is None

    def test_retrieve_by_topics(self, tmp_path):
        store = MemoryStore(store_dir=tmp_path / "memories")
        store.add(MemoryItem(content="auth info", category=MemoryCategory.file_knowledge, topics=["auth", "jwt"]))
        store.add(MemoryItem(content="db info", category=MemoryCategory.file_knowledge, topics=["database", "sql"]))
        results = store.retrieve_by_topics(["auth"])
        assert len(results) == 1
        assert "auth" in results[0].content

    def test_enforce_capacity(self, tmp_path):
        store = MemoryStore(store_dir=tmp_path / "memories")
        for i in range(5):
            store.add(MemoryItem(content=f"item {i}", category=MemoryCategory.patterns, topics=["test"]))
        store.add(MemoryItem(content="pref", category=MemoryCategory.preferences, topics=["pref"]))
        store.enforce_capacity(max_items=3)
        all_items = store.all_items
        assert len(all_items) <= 3
        pref_items = [i for i in all_items if i.category == MemoryCategory.preferences]
        assert len(pref_items) == 1
