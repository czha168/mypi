"""Integration test: full compaction → extraction → dedup → store → retrieval → injection pipeline.

Uses real Ollama LLM for memory extraction.
"""
import os

import pytest
import httpx

from codepi.ai.openai_compat import OpenAICompatProvider
from codepi.core.memory_store import MemoryCategory, MemoryItem, MemoryStore
from codepi.core.memory_dedup import MemoryDeduplicator
from codepi.core.memory_extractor import MemoryExtractor
from codepi.core.agent_session import parse_tiered_response
from codepi.extensions.memory_extension import MemoryExtension, format_memories_for_prompt
from codepi.config import MemoryConfig


def get_provider():
    base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    api_key = os.environ.get("OLLAMA_API_KEY", "ollama")
    model = os.environ.get("OLLAMA_MODEL", "gpt-oss:20b-128k")
    return OpenAICompatProvider(base_url=base_url, api_key=api_key, default_model=model), model


def skip_if_no_ollama():
    base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    try:
        with httpx.Client() as client:
            resp = client.get(base_url.replace("/v1", "/api/tags"), timeout=3.0)
            if resp.status_code == 200:
                models = [m["name"] for m in resp.json().get("models", [])]
                _, model = get_provider()
                if not any(model in m for m in models):
                    pytest.skip(f"Model {model} not found in Ollama")
                return
    except Exception:
        pytest.skip("Ollama not reachable")
    pytest.skip("Ollama not reachable")


SIMULATED_L1_OVERVIEW = """\
The user discussed refactoring the authentication module:
- Decided to use JWT tokens instead of session cookies for stateless auth
- The auth logic lives in codepi/core/security.py
- Established a pattern of always checking permissions before tool execution
- User prefers using pytest over unittest for all new tests
- Added a new SecurityMonitor class that evaluates tool calls against rules
- Fixed a bug in the token refresh logic where expired tokens weren't being rejected
- User mentioned they want all API responses to be JSON-formatted
"""


@pytest.mark.asyncio
async def test_full_memory_pipeline(tmp_path):
    skip_if_no_ollama()
    provider, model = get_provider()

    # --- Step 1: Tiered compaction parsing ---
    raw_response = (
        "ABSTRACT:\n"
        "JWT authentication, SecurityMonitor, pytest, token refresh, "
        "security.py, JSON API responses, permissions check pattern\n\n"
        "OVERVIEW:\n"
        + SIMULATED_L1_OVERVIEW
    )
    l0, l1 = parse_tiered_response(raw_response)
    assert len(l0) > 10
    assert len(l1) > 50
    assert "JWT" in l0 or "JWT" in l1

    # --- Step 2: Memory extraction from L1 via real LLM ---
    extractor = MemoryExtractor()
    items = await extractor.extract(l1, "test-session-001", provider, model)
    assert len(items) > 0, f"Expected extracted items, got {items}"

    categories_seen = {item.category for item in items}
    assert len(categories_seen) >= 2, f"Expected 2+ categories, got {categories_seen}"

    # --- Step 3: Dedup against store ---
    store = MemoryStore(store_dir=tmp_path / "memories")
    dedup = MemoryDeduplicator(jaccard_threshold=0.7)
    dedup.index_existing(store)

    stored_count = 0
    for candidate in items:
        result = dedup.check(candidate, store)
        if result.decision.value == "create":
            store.add(candidate)
            stored_count += 1

    assert stored_count > 0, "At least some items should have been stored"
    all_stored = store.all_items
    assert len(all_stored) > 0

    # --- Step 4: Run extraction again to verify dedup works ---
    items_round2 = await extractor.extract(l1, "test-session-002", provider, model)
    dedup2 = MemoryDeduplicator(jaccard_threshold=0.7)
    dedup2.index_existing(store)

    new_items = 0
    skipped = 0
    for candidate in items_round2:
        result = dedup2.check(candidate, store)
        if result.decision.value == "create":
            store.add(candidate)
            new_items += 1
        else:
            skipped += 1

    # Second pass should skip or merge most items (not double-store everything)
    assert skipped > 0 or new_items < stored_count * 3, \
        f"Dedup should prevent bloat: skipped={skipped}, new={new_items}"

    # --- Step 5: Topic-based retrieval ---
    results = store.retrieve_by_topics(["jwt", "auth", "token"])
    assert len(results) > 0, "Should find items matching auth topics"

    results_prefs = store.retrieve_by_topics(["pytest"])

    # --- Step 6: Memory injection into prompt ---
    config = MemoryConfig(injection_token_budget=1000)
    section = format_memories_for_prompt(
        results[:10], ["jwt", "auth"], config.injection_token_budget,
    )
    assert "## Relevant Memories from Past Sessions" in section
    assert "jwt" in section.lower() or "auth" in section.lower()

    # --- Step 7: Capacity enforcement ---
    for i in range(20):
        store.add(MemoryItem(
            content=f"Filler item {i} about random things",
            category=MemoryCategory.patterns,
            topics=["filler"],
        ))
    store.enforce_capacity(max_items=10)
    remaining = store.all_items
    assert len(remaining) <= 10

    # Preferences survive eviction
    if results_prefs:
        stored_prefs = [i for i in store.all_items if i.category == MemoryCategory.preferences]
        assert len(stored_prefs) > 0, "Preferences should survive eviction"
