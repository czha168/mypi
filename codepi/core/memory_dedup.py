from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from enum import Enum

from codepi.core.memory_store import MemoryItem, MemoryStore

logger = logging.getLogger(__name__)


class DedupDecision(str, Enum):
    skip = "skip"
    create = "create"
    merge = "merge"


@dataclass
class DedupResult:
    decision: DedupDecision
    matched_id: str | None = None
    similarity_score: float = 0.0


def compute_content_hash(content: str) -> str:
    """Normalize whitespace, lowercase, SHA-256."""
    normalized = " ".join(content.lower().split())
    return hashlib.sha256(normalized.encode()).hexdigest()


def compute_jaccard_similarity(text_a: str, text_b: str) -> float:
    """Tokenize, compute set intersection/union ratio."""
    set_a = set(text_a.lower().split())
    set_b = set(text_b.lower().split())
    if not set_a and not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union) if union else 0.0


class MemoryDeduplicator:
    def __init__(self, jaccard_threshold: float = 0.7):
        self.jaccard_threshold = jaccard_threshold
        self._hash_index: dict[str, str] = {}  # content_hash -> item_id

    def index_existing(self, store: MemoryStore) -> None:
        """Build hash index from existing store items."""
        for item in store.all_items:
            content_hash = compute_content_hash(item.content)
            self._hash_index[content_hash] = item.id

    def check(self, candidate: MemoryItem, store: MemoryStore) -> DedupResult:
        """Check candidate against store for duplicates."""
        candidate_hash = compute_content_hash(candidate.content)

        # Step 1: Exact hash match → skip
        if candidate_hash in self._hash_index:
            matched_id = self._hash_index[candidate_hash]
            logger.debug("Exact dup detected: %s → %s", candidate.id[:8], matched_id[:8])
            return DedupResult(
                decision=DedupDecision.skip,
                matched_id=matched_id,
                similarity_score=1.0,
            )

        # Step 2: Jaccard similarity check
        best_similarity = 0.0
        best_match_id: str | None = None

        for item in store.all_items:
            sim = compute_jaccard_similarity(candidate.content, item.content)
            if sim > best_similarity:
                best_similarity = sim
                best_match_id = item.id

        # High overlap → merge
        if best_similarity > self.jaccard_threshold and best_match_id:
            logger.debug(
                "High Jaccard %.2f: %s → %s", best_similarity,
                candidate.id[:8], best_match_id[:8],
            )
            return DedupResult(
                decision=DedupDecision.merge,
                matched_id=best_match_id,
                similarity_score=best_similarity,
            )

        # No significant match → create
        if candidate_hash not in self._hash_index:
            self._hash_index[candidate_hash] = candidate.id

        return DedupResult(
            decision=DedupDecision.create,
            similarity_score=best_similarity,
        )

    @staticmethod
    def merge_content(existing: str, candidate: str) -> str:
        """Keep longer/more detailed version."""
        return candidate if len(candidate) > len(existing) else existing
