from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from codepi.core.memory_store import MemoryCategory, MemoryItem

if TYPE_CHECKING:
    from codepi.ai.provider import LLMProvider

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT_TEMPLATE = """\
Analyze the following conversation segment and extract reusable knowledge items.
For each item, provide:
1. "category": one of "decisions" (architectural/technical choices), "patterns" (recurring code patterns/idioms), "file-knowledge" (project-specific file/function mappings), or "preferences" (user's stated preferences)
2. "content": a concise description of the knowledge (1-3 sentences)
3. "topics": a list of relevant keyword tags

Respond with a JSON array. If no meaningful knowledge can be extracted, respond with an empty array [].

Conversation segment:
{l1_overview}"""

_STOPWORDS = frozenset({
    "that", "this", "with", "from", "have", "been", "were", "will", "would",
    "could", "should", "their", "there", "about", "which", "when", "what",
    "your", "they", "into", "than", "them", "then", "also", "just", "some",
    "very", "much", "more", "most", "only", "over", "such", "like", "does",
    "before", "after", "between", "through", "during", "without", "within",
    "along", "following", "across", "behind", "beyond", "plus", "except",
    "upon", "among",
})


def extract_topics(text: str) -> list[str]:
    """Tokenize, filter stopwords, keep significant words (length > 3)."""
    tokens = re.findall(r"[a-z]{4,}", text.lower())
    return sorted({t for t in tokens if t not in _STOPWORDS})


class MemoryExtractor:
    def __init__(self) -> None:
        pass

    async def extract(
        self,
        l1_overview: str,
        session_id: str,
        provider: LLMProvider,
        model: str,
    ) -> list[MemoryItem]:
        """Extract memories from L1 overview via LLM call."""
        from codepi.ai.provider import TokenEvent  # avoid circular at module level

        prompt = EXTRACTION_PROMPT_TEMPLATE.format(l1_overview=l1_overview)
        messages = [{"role": "user", "content": prompt}]

        response_parts: list[str] = []
        async for event in provider.stream(
            messages=messages, tools=[], model=model, system="",
        ):
            if isinstance(event, TokenEvent):
                response_parts.append(event.text)

        raw = "".join(response_parts)
        parsed = self._parse_json_response(raw)
        if parsed is None:
            logger.warning("Failed to parse memory extraction response")
            return []

        items: list[MemoryItem] = []
        now = datetime.now(timezone.utc).isoformat()
        for entry in parsed:
            cat_str = entry.get("category", "")
            try:
                category = MemoryCategory(cat_str)
            except ValueError:
                logger.debug("Skipping unknown category: %s", cat_str)
                continue

            content = entry.get("content", "")
            if not content:
                continue

            topics = entry.get("topics", [])
            if not topics:
                topics = extract_topics(content)

            items.append(MemoryItem(
                id=str(uuid.uuid4()),
                content=content,
                category=category,
                topics=topics,
                source_session_id=session_id,
                created_at=now,
                updated_at=now,
            ))

        return items

    async def extract_from_messages(
        self,
        messages: list[dict],
        session_id: str,
        provider: LLMProvider,
        model: str,
    ) -> list[MemoryItem]:
        """Fallback extraction from raw messages."""
        parts: list[str] = []
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str) and content:
                parts.append(content)
        combined = "\n".join(parts)[:2000]
        if not combined.strip():
            return []
        return await self.extract(combined, session_id, provider, model)

    @staticmethod
    def _parse_json_response(raw: str) -> list[dict] | None:
        """Parse JSON array from LLM response, handling markdown code blocks."""
        text = raw.strip()
        # Try direct parse
        try:
            result = json.loads(text)
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass
        # Try extracting from markdown code block
        match = re.search(r"```(?:json)?\s*\n(.*?)\n```", text, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group(1))
                if isinstance(result, list):
                    return result
            except json.JSONDecodeError:
                pass
        return None
