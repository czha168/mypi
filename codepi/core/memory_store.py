from __future__ import annotations

import json
import logging
import math
import os
import tempfile
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class MemoryCategory(str, Enum):
    decisions = "decisions"
    patterns = "patterns"
    file_knowledge = "file-knowledge"
    preferences = "preferences"


@dataclass
class MemoryItem:
    content: str
    category: MemoryCategory
    topics: list[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_session_id: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    access_count: int = 0
    hotness_score: float = 0.0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "content": self.content,
            "category": self.category.value,
            "topics": self.topics,
            "source_session_id": self.source_session_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "access_count": self.access_count,
            "hotness_score": self.hotness_score,
        }

    @classmethod
    def from_dict(cls, d: dict) -> MemoryItem:
        return cls(
            id=d["id"],
            content=d["content"],
            category=MemoryCategory(d["category"]),
            topics=d.get("topics", []),
            source_session_id=d.get("source_session_id", ""),
            created_at=d.get("created_at", ""),
            updated_at=d.get("updated_at", ""),
            access_count=d.get("access_count", 0),
            hotness_score=d.get("hotness_score", 0.0),
        )


def compute_hotness(access_count: int, updated_at: str, half_life_days: float = 7.0) -> float:
    """Compute hotness score: sigmoid(log1p(count)) * time_decay(updated_at)."""
    # Sigmoid component: sigmoid(log1p(access_count))
    x = math.log1p(access_count)
    sigmoid = 1.0 / (1.0 + math.exp(-x))

    # Time decay: 0.5 ^ (age_days / half_life)
    if updated_at:
        try:
            updated = datetime.fromisoformat(updated_at)
            if updated.tzinfo is None:
                updated = updated.replace(tzinfo=timezone.utc)
            age = datetime.now(timezone.utc) - updated
            age_days = age.total_seconds() / 86400.0
        except (ValueError, TypeError):
            age_days = 0.0
    else:
        age_days = 0.0

    decay = 0.5 ** (age_days / half_life_days)
    return sigmoid * decay


class MemoryStore:
    def __init__(self, store_dir: Path | None = None):
        self.store_dir = store_dir or Path.home() / ".codepi" / "memories"
        self.items_dir = self.store_dir / "items"
        self.index_path = self.store_dir / "index.json"
        self.items_dir.mkdir(parents=True, exist_ok=True)
        self._index: dict[str, dict] = self._load_index()

    def _load_index(self) -> dict[str, dict]:
        """Load index.json manifest."""
        if self.index_path.exists():
            try:
                data = json.loads(self.index_path.read_text())
                return data if isinstance(data, dict) else {}
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Failed to load memory index: %s", e)
        return {}

    def _save_index(self) -> None:
        """Atomic write of index.json."""
        data = json.dumps(self._index, indent=2)
        self._atomic_write(self.index_path, data)

    def _atomic_write(self, path: Path, content: str) -> None:
        """Write file atomically: temp file then rename."""
        fd, tmp = tempfile.mkstemp(dir=str(path.parent))
        try:
            os.write(fd, content.encode())
            os.close(fd)
            os.replace(tmp, str(path))
        except BaseException:
            os.close(fd) if not os.get_inheritable(fd) else None
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    def _item_path(self, item_id: str) -> Path:
        return self.items_dir / f"{item_id[:8]}.json"

    def add(self, item: MemoryItem) -> None:
        """Write item to disk and update index."""
        item.hotness_score = compute_hotness(item.access_count, item.updated_at)
        path = self._item_path(item.id)
        self._atomic_write(path, json.dumps(item.to_dict(), indent=2))
        self._index[item.id] = {
            "id": item.id,
            "category": item.category.value,
            "topics": item.topics,
            "access_count": item.access_count,
            "updated_at": item.updated_at,
            "hotness_score": item.hotness_score,
            "file_path": str(path.relative_to(self.store_dir)),
        }
        self._save_index()

    def get(self, item_id: str) -> MemoryItem | None:
        """Read item from disk."""
        meta = self._index.get(item_id)
        if not meta:
            return None
        path = self.store_dir / meta["file_path"]
        if not path.exists():
            return None
        try:
            return MemoryItem.from_dict(json.loads(path.read_text()))
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Failed to read memory item %s: %s", item_id, e)
            return None

    def update(self, item_id: str, **fields) -> None:
        """Update fields, recalculate hotness, rewrite file and index."""
        item = self.get(item_id)
        if item is None:
            return
        for k, v in fields.items():
            if hasattr(item, k):
                setattr(item, k, v)
        item.updated_at = datetime.now(timezone.utc).isoformat()
        item.hotness_score = compute_hotness(item.access_count, item.updated_at)
        path = self._item_path(item.id)
        self._atomic_write(path, json.dumps(item.to_dict(), indent=2))
        self._index[item.id] = {
            "id": item.id,
            "category": item.category.value,
            "topics": item.topics,
            "access_count": item.access_count,
            "updated_at": item.updated_at,
            "hotness_score": item.hotness_score,
            "file_path": str(path.relative_to(self.store_dir)),
        }
        self._save_index()

    def delete(self, item_id: str) -> None:
        """Remove file and index entry."""
        meta = self._index.pop(item_id, None)
        if meta:
            path = self.store_dir / meta["file_path"]
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
            self._save_index()

    def retrieve_by_topics(self, keywords: list[str], limit: int = 20) -> list[MemoryItem]:
        """Filter by topic overlap, sort by hotness desc."""
        kw_set = {k.lower() for k in keywords}
        matched: list[tuple[float, str]] = []
        for item_id, meta in self._index.items():
            topics = {t.lower() for t in meta.get("topics", [])}
            if kw_set & topics:
                matched.append((meta.get("hotness_score", 0.0), item_id))

        matched.sort(key=lambda x: x[0], reverse=True)
        results: list[MemoryItem] = []
        for _, item_id in matched[:limit]:
            item = self.get(item_id)
            if item:
                results.append(item)
        return results

    def enforce_capacity(self, max_items: int = 500) -> None:
        """Evict lowest-hotness items, exempting preferences."""
        while len(self._index) > max_items:
            # Find lowest hotness non-preferences item
            candidates = [
                (meta.get("hotness_score", 0.0), item_id)
                for item_id, meta in self._index.items()
                if meta.get("category") != "preferences"
            ]
            if not candidates:
                break
            candidates.sort(key=lambda x: x[0])
            _, evict_id = candidates[0]
            self.delete(evict_id)

    @property
    def all_items(self) -> list[MemoryItem]:
        """Return all items from index."""
        results: list[MemoryItem] = []
        for item_id in self._index:
            item = self.get(item_id)
            if item:
                results.append(item)
        return results
