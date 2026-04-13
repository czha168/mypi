from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from codepi.core.memory_store import MemoryStore, compute_hotness
from codepi.core.memory_extractor import extract_topics
from codepi.extensions.base import Extension

if TYPE_CHECKING:
    from codepi.core.events import BeforeAgentStartEvent
    from codepi.config import MemoryConfig

logger = logging.getLogger(__name__)

MEMORY_SECTION_HEADER = "## Relevant Memories from Past Sessions"


def format_memories_for_prompt(
    items: list, keywords: list[str], token_budget: int,
) -> str:
    if not items:
        return ""
    kw_set = {k.lower() for k in keywords}
    scored: list[tuple[float, str]] = []
    for item in items:
        topic_overlap = len({t.lower() for t in item.topics} & kw_set) / max(len(kw_set), 1)
        blended = 0.8 * topic_overlap + 0.2 * item.hotness_score
        line = f"[{item.category.value}] {item.content}"
        scored.append((blended, line))
    scored.sort(key=lambda x: x[0], reverse=True)

    lines: list[str] = [MEMORY_SECTION_HEADER]
    budget = token_budget
    for _, line in scored:
        est_tokens = len(line) // 4
        if est_tokens > budget:
            break
        lines.append(line)
        budget -= est_tokens
    return "\n".join(lines) if len(lines) > 1 else ""


class MemoryExtension(Extension):
    name = "memory"

    def __init__(self, config: MemoryConfig | None = None):
        self._config = config
        self._store: MemoryStore | None = None

    def _ensure_store(self) -> MemoryStore | None:
        if self._store is not None:
            return self._store
        try:
            self._store = MemoryStore()
            return self._store
        except Exception as e:
            logger.warning("Memory store unavailable: %s", e)
            return None

    async def on_before_agent_start(self, event: BeforeAgentStartEvent) -> BeforeAgentStartEvent | None:
        store = self._ensure_store()
        if store is None:
            return None

        keywords: list[str] = []
        user_messages = [m for m in event.messages if m.get("role") == "user"]
        for msg in user_messages[-3:]:
            keywords.extend(extract_topics(msg.get("content", "")))
        keywords = list(set(keywords))
        if not keywords:
            return None

        try:
            items = store.retrieve_by_topics(keywords, limit=20)
        except Exception as e:
            logger.warning("Memory retrieval failed: %s", e)
            return None

        if not items:
            return None

        budget = self._config.injection_token_budget if self._config else 1000
        section = format_memories_for_prompt(items, keywords, budget)
        if not section:
            return None

        return BeforeAgentStartEvent(
            system_prompt=event.system_prompt + "\n\n" + section,
            messages=event.messages,
        )
