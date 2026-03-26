# mypi Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a minimalist terminal-based Python coding assistant with OpenAI-compatible LLM backend, tree-structured sessions, 7 built-in tools, hot-reloadable Python extensions, Claude Code–compatible skills, and a rich+prompt_toolkit TUI.

**Architecture:** Single `mypi` package with 6 submodules layered bottom-up: `ai/` → `core/` → `tools/` → `extensions/` → `tui/` → `modes/`. Each layer depends only on layers below it. `AgentSession` is the central runtime that wires everything together.

**Tech Stack:** Python 3.11+, `openai>=1.0`, `rich>=13.0`, `prompt_toolkit>=3.0`, `watchdog>=4.0`, `pyyaml>=6.0`, `pytest`, stdlib `tomllib`, `asyncio`

---

## File Map

```
mypi/
├── __init__.py
├── __main__.py                    # Task 23: CLI entry point
├── config.py                      # Task 16: Config loading
├── ai/
│   ├── __init__.py
│   ├── provider.py                # Task 3: LLMProvider ABC + ProviderEvent types
│   └── openai_compat.py           # Task 4: OpenAI-compatible streaming impl
├── core/
│   ├── __init__.py
│   ├── events.py                  # Task 2: Typed event dataclasses
│   ├── agent_session.py           # Tasks 14–15: LLM loop, retry, compaction
│   └── session_manager.py        # Tasks 5–7: JSONL tree persistence
├── tools/
│   ├── __init__.py
│   ├── base.py                    # Task 8: Tool ABC, ToolResult, ToolRegistry, ExtensionRunner
│   └── builtins.py               # Tasks 9–10: 7 built-in tools
├── extensions/
│   ├── __init__.py
│   ├── base.py                    # Task 11: Extension ABC + UIComponents
│   ├── skill_loader.py           # Task 12: Markdown skill parser
│   └── loader.py                 # Task 13: Python extension loader + hot-reload
├── tui/
│   ├── __init__.py
│   ├── renderer.py               # Task 20: Rich streaming markdown renderer
│   ├── components.py             # Task 21: Input area, status bar, tool call display
│   └── app.py                    # Task 21: prompt_toolkit Application setup
└── modes/
    ├── __init__.py
    ├── print_mode.py             # Task 17: Streaming stdout mode
    ├── rpc.py                    # Task 18: JSONL stdin/stdout mode
    ├── sdk.py                    # Task 19: Embeddable Python API
    └── interactive.py            # Task 22: Full TUI mode

tests/
├── conftest.py                   # Task 1: Shared fixtures (mock provider, tmp dirs)
├── ai/
│   └── test_provider.py          # Tasks 3–4
├── core/
│   ├── test_events.py            # Task 2
│   ├── test_session_manager.py   # Tasks 5–7
│   └── test_agent_session.py     # Tasks 14–15
├── tools/
│   ├── test_base.py              # Task 8
│   └── test_builtins.py          # Tasks 9–10
├── extensions/
│   ├── test_base.py              # Task 11
│   ├── test_skill_loader.py      # Task 12
│   └── test_loader.py            # Task 13
└── modes/
    ├── test_print_mode.py        # Task 17
    ├── test_rpc.py               # Task 18
    └── test_sdk.py               # Task 19
```

---

## Task 1: Project Scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `mypi/__init__.py` (and all subpackage `__init__.py` files)
- Create: `tests/conftest.py`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "mypi"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "openai>=1.0",
    "rich>=13.0",
    "prompt_toolkit>=3.0",
    "watchdog>=4.0",
    "pyyaml>=6.0",
]

[project.scripts]
mypi = "mypi.__main__:main"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-asyncio>=0.23", "pytest-mock>=3.0"]
```

- [ ] **Step 2: Create package skeleton**

```bash
mkdir -p mypi/{ai,core,tools,extensions,tui,modes}
mkdir -p tests/{ai,core,tools,extensions,modes}
touch mypi/__init__.py mypi/ai/__init__.py mypi/core/__init__.py
touch mypi/tools/__init__.py mypi/extensions/__init__.py
touch mypi/tui/__init__.py mypi/modes/__init__.py
touch tests/__init__.py tests/ai/__init__.py tests/core/__init__.py
touch tests/tools/__init__.py tests/extensions/__init__.py tests/modes/__init__.py
```

- [ ] **Step 3: Create `tests/conftest.py`**

```python
import asyncio
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def tmp_sessions_dir(tmp_path):
    d = tmp_path / "sessions"
    d.mkdir()
    return d


@pytest.fixture
def tmp_skills_dir(tmp_path):
    d = tmp_path / "skills"
    d.mkdir()
    return d


@pytest.fixture
def tmp_extensions_dir(tmp_path):
    d = tmp_path / "extensions"
    d.mkdir()
    return d
```

- [ ] **Step 4: Install in dev mode**

```bash
pip install -e ".[dev]"
```

Expected: installs without errors, `pytest --collect-only` shows 0 tests.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml mypi/ tests/
git commit -m "feat: scaffold mypi package structure"
```

---

## Task 2: Events Layer

**Files:**
- Create: `mypi/core/events.py`
- Create: `tests/core/test_events.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/core/test_events.py
from codepi.core.events import (
    BeforeAgentStartEvent, BeforeProviderRequestEvent,
    ToolCallEvent, ToolResultEvent,
    SessionForkEvent, SessionTreeEvent,
    AutoCompactionStartEvent, AutoCompactionEndEvent,
    AutoRetryStartEvent, AutoRetryEndEvent,
)
from codepi.tools.base import ToolResult


def test_before_agent_start_event_is_mutable():
    evt = BeforeAgentStartEvent(system_prompt="hello", messages=[])
    evt2 = BeforeAgentStartEvent(system_prompt="modified", messages=[{"role": "user", "content": "hi"}])
    assert evt.system_prompt == "hello"
    assert evt2.system_prompt == "modified"


def test_tool_call_event_fields():
    evt = ToolCallEvent(tool_name="read", arguments={"path": "foo.py"})
    assert evt.tool_name == "read"
    assert evt.arguments == {"path": "foo.py"}


def test_tool_result_event_fields():
    result = ToolResult(output="file contents")
    evt = ToolResultEvent(tool_name="read", result=result)
    assert evt.result.output == "file contents"


def test_notification_events():
    fork = SessionForkEvent(from_entry_id="a", new_entry_id="b")
    tree = SessionTreeEvent(leaf_id="c")
    compaction_start = AutoCompactionStartEvent()
    compaction_end = AutoCompactionEndEvent(summary="summarized 10 messages")
    retry_start = AutoRetryStartEvent(attempt=1)
    retry_end = AutoRetryEndEvent(attempt=1)
    assert fork.from_entry_id == "a"
    assert tree.leaf_id == "c"
    assert compaction_end.summary == "summarized 10 messages"
    assert retry_start.attempt == 1
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/core/test_events.py -v
```

Expected: ImportError — module not found.

- [ ] **Step 3: Implement `mypi/core/events.py`**

```python
from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from codepi.tools.base import ToolResult


# ---------------------------------------------------------------------------
# Mutable events — extensions return EventType | None (None = no-op)
# ---------------------------------------------------------------------------

@dataclass
class BeforeAgentStartEvent:
    system_prompt: str
    messages: list[dict]


@dataclass
class BeforeProviderRequestEvent:
    params: dict


@dataclass
class ToolCallEvent:
    tool_name: str
    arguments: dict


@dataclass
class ToolResultEvent:
    tool_name: str
    result: "ToolResult"


# ---------------------------------------------------------------------------
# Notification events — extensions return None (observation only)
# ---------------------------------------------------------------------------

@dataclass
class SessionForkEvent:
    from_entry_id: str
    new_entry_id: str


@dataclass
class SessionTreeEvent:
    leaf_id: str


@dataclass
class TokenStreamEvent:
    """Internal rendering use only — not dispatched to extensions."""
    text: str


@dataclass
class AutoCompactionStartEvent:
    pass


@dataclass
class AutoCompactionEndEvent:
    summary: str


@dataclass
class AutoRetryStartEvent:
    attempt: int


@dataclass
class AutoRetryEndEvent:
    attempt: int
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/core/test_events.py -v
```

Expected: All PASS. Note: `ToolResult` import will require `mypi/tools/base.py` to exist with a `ToolResult` class. Create a stub now:

```python
# mypi/tools/base.py (stub — full implementation in Task 8)
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolResult:
    output: str = ""
    error: str | None = None
    metadata: dict = field(default_factory=dict)
```

- [ ] **Step 5: Commit**

```bash
git add mypi/core/events.py mypi/tools/base.py tests/core/test_events.py
git commit -m "feat: add typed event dataclasses and ToolResult stub"
```

---

## Task 3: AI Provider ABC

**Files:**
- Create: `mypi/ai/provider.py`
- Create: `tests/ai/test_provider.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/ai/test_provider.py
import pytest
from codepi.ai.provider import LLMProvider, TokenEvent, LLMToolCallEvent, DoneEvent, TokenUsage


def test_provider_event_types():
    tok = TokenEvent(text="hello")
    tool = LLMToolCallEvent(id="c1", name="read", arguments={"path": "x"})
    done = DoneEvent(usage=TokenUsage(input_tokens=100, output_tokens=50))
    assert tok.text == "hello"
    assert tool.name == "read"
    assert done.usage.input_tokens == 100


def test_llm_provider_is_abstract():
    import inspect
    assert inspect.isabstract(LLMProvider)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/ai/test_provider.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `mypi/ai/provider.py`**

```python
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator, Union


@dataclass
class TokenEvent:
    text: str


@dataclass
class LLMToolCallEvent:
    """Emitted by provider when LLM requests a tool. Distinct from core ToolCallEvent."""
    id: str
    name: str
    arguments: dict


@dataclass
class TokenUsage:
    input_tokens: int
    output_tokens: int


@dataclass
class DoneEvent:
    usage: TokenUsage


ProviderEvent = Union[TokenEvent, LLMToolCallEvent, DoneEvent]


class LLMProvider(ABC):
    @abstractmethod
    async def stream(
        self,
        messages: list[dict],
        tools: list[dict],
        model: str,
        system: str,
        **kwargs,
    ) -> AsyncIterator[ProviderEvent]: ...
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/ai/test_provider.py -v
```

Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add mypi/ai/provider.py tests/ai/test_provider.py
git commit -m "feat: add LLMProvider ABC and ProviderEvent types"
```

---

## Task 4: OpenAI-Compatible Provider

**Files:**
- Create: `mypi/ai/openai_compat.py`
- Modify: `tests/ai/test_provider.py`

- [ ] **Step 1: Write the failing test**

```python
# Append to tests/ai/test_provider.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from codepi.ai.openai_compat import OpenAICompatProvider


@pytest.mark.asyncio
async def test_openai_compat_streams_tokens():
    provider = OpenAICompatProvider(base_url="http://localhost", api_key="test", default_model="gpt-4o")

    # Mock the openai client stream
    chunk1 = MagicMock()
    chunk1.choices = [MagicMock(delta=MagicMock(content="Hello", tool_calls=None))]
    chunk1.usage = None

    final_chunk = MagicMock()
    final_chunk.choices = [MagicMock(delta=MagicMock(content=None, tool_calls=None))]
    final_chunk.usage = MagicMock(prompt_tokens=10, completion_tokens=5)

    mock_stream = AsyncMock()
    mock_stream.__aiter__ = AsyncMock(return_value=iter([chunk1, final_chunk]))

    with patch.object(provider._client.chat.completions, "create", return_value=mock_stream):
        events = []
        async for event in provider.stream(messages=[], tools=[], model="gpt-4o", system=""):
            events.append(event)

    token_events = [e for e in events if isinstance(e, TokenEvent)]
    done_events = [e for e in events if isinstance(e, DoneEvent)]
    assert any(e.text == "Hello" for e in token_events)
    assert len(done_events) == 1


@pytest.mark.asyncio
async def test_openai_compat_emits_tool_call():
    provider = OpenAICompatProvider(base_url="http://localhost", api_key="test", default_model="gpt-4o")

    tool_chunk = MagicMock()
    tool_call = MagicMock()
    tool_call.id = "call_abc"
    tool_call.function.name = "read"
    tool_call.function.arguments = '{"path": "foo.py"}'
    tool_chunk.choices = [MagicMock(delta=MagicMock(content=None, tool_calls=[tool_call]))]
    tool_chunk.usage = None

    final_chunk = MagicMock()
    final_chunk.choices = [MagicMock(delta=MagicMock(content=None, tool_calls=None))]
    final_chunk.usage = MagicMock(prompt_tokens=20, completion_tokens=10)

    mock_stream = AsyncMock()
    mock_stream.__aiter__ = AsyncMock(return_value=iter([tool_chunk, final_chunk]))

    with patch.object(provider._client.chat.completions, "create", return_value=mock_stream):
        events = []
        async for event in provider.stream(messages=[], tools=[], model="gpt-4o", system=""):
            events.append(event)

    tool_events = [e for e in events if isinstance(e, LLMToolCallEvent)]
    assert len(tool_events) == 1
    assert tool_events[0].name == "read"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/ai/test_provider.py::test_openai_compat_streams_tokens -v
```

Expected: ImportError — `openai_compat` not found.

- [ ] **Step 3: Implement `mypi/ai/openai_compat.py`**

```python
from __future__ import annotations
import json
from typing import AsyncIterator
import openai
from codepi.ai.provider import LLMProvider, ProviderEvent, TokenEvent, LLMToolCallEvent, DoneEvent, TokenUsage


class OpenAICompatProvider(LLMProvider):
    def __init__(self, base_url: str, api_key: str, default_model: str = "gpt-4o"):
        self.default_model = default_model
        self._client = openai.AsyncOpenAI(base_url=base_url, api_key=api_key)

    async def stream(
        self,
        messages: list[dict],
        tools: list[dict],
        model: str,
        system: str,
        **kwargs,
    ) -> AsyncIterator[ProviderEvent]:
        full_messages = ([{"role": "system", "content": system}] if system else []) + messages
        create_kwargs = dict(model=model, messages=full_messages, stream=True, **kwargs)
        if tools:
            create_kwargs["tools"] = tools

        # Accumulate streaming tool call arguments (may arrive in multiple chunks)
        pending_tool_calls: dict[int, dict] = {}

        async with await self._client.chat.completions.create(**create_kwargs) as stream:
            async for chunk in stream:
                choice = chunk.choices[0] if chunk.choices else None
                if choice is None:
                    if chunk.usage:
                        yield DoneEvent(usage=TokenUsage(
                            input_tokens=chunk.usage.prompt_tokens,
                            output_tokens=chunk.usage.completion_tokens,
                        ))
                    continue

                delta = choice.delta

                if delta.content:
                    yield TokenEvent(text=delta.content)

                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index
                        if idx not in pending_tool_calls:
                            pending_tool_calls[idx] = {"id": tc.id, "name": tc.function.name, "arguments": ""}
                        if tc.function.arguments:
                            pending_tool_calls[idx]["arguments"] += tc.function.arguments

                if choice.finish_reason in ("tool_calls", "stop"):
                    for tc in pending_tool_calls.values():
                        yield LLMToolCallEvent(
                            id=tc["id"],
                            name=tc["name"],
                            arguments=json.loads(tc["arguments"] or "{}"),
                        )
                    pending_tool_calls.clear()

                if chunk.usage:
                    yield DoneEvent(usage=TokenUsage(
                        input_tokens=chunk.usage.prompt_tokens,
                        output_tokens=chunk.usage.completion_tokens,
                    ))
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/ai/ -v
```

Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add mypi/ai/openai_compat.py tests/ai/test_provider.py
git commit -m "feat: implement OpenAI-compatible streaming provider"
```

---

## Task 5: Session Manager — Core CRUD + Tree Structure

**Files:**
- Create: `mypi/core/session_manager.py`
- Create: `tests/core/test_session_manager.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/core/test_session_manager.py
import json
import pytest
from pathlib import Path
from codepi.core.session_manager import SessionManager, SessionEntry


def test_append_creates_jsonl_file(tmp_sessions_dir):
    sm = SessionManager(sessions_dir=tmp_sessions_dir)
    session_id = sm.new_session(model="gpt-4o")
    sm.append(SessionEntry(type="message", data={"role": "user", "content": "hello"}))
    path = tmp_sessions_dir / f"{session_id}.jsonl"
    assert path.exists()
    lines = path.read_text().strip().split("\n")
    assert len(lines) == 2  # session_info + message


def test_parent_id_chains_correctly(tmp_sessions_dir):
    sm = SessionManager(sessions_dir=tmp_sessions_dir)
    sm.new_session(model="gpt-4o")
    sm.append(SessionEntry(type="message", data={"role": "user", "content": "a"}))
    sm.append(SessionEntry(type="message", data={"role": "assistant", "content": "b"}))
    entries = sm.load_all_entries()
    # Check parent chain: session_info -> msg1 -> msg2
    assert entries[1].parent_id == entries[0].id
    assert entries[2].parent_id == entries[1].id


def test_branch_creates_new_leaf(tmp_sessions_dir):
    sm = SessionManager(sessions_dir=tmp_sessions_dir)
    sm.new_session(model="gpt-4o")
    sm.append(SessionEntry(type="message", data={"role": "user", "content": "a"}))
    entry_a = sm.current_leaf_id
    sm.append(SessionEntry(type="message", data={"role": "assistant", "content": "b"}))

    # Branch from entry_a
    sm.branch(entry_a)
    sm.append(SessionEntry(type="message", data={"role": "user", "content": "branch msg"}))

    leaf_ids = sm.get_leaf_ids()
    assert len(leaf_ids) == 2


def test_list_sessions(tmp_sessions_dir):
    sm1 = SessionManager(sessions_dir=tmp_sessions_dir)
    sm1.new_session(model="gpt-4o")
    sm2 = SessionManager(sessions_dir=tmp_sessions_dir)
    sm2.new_session(model="gpt-4o")
    sessions = SessionManager.list_sessions(tmp_sessions_dir)
    assert len(sessions) == 2
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/core/test_session_manager.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `mypi/core/session_manager.py` (core structure)**

```python
from __future__ import annotations
import json
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any


@dataclass
class SessionEntry:
    type: str
    data: dict = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_id: str | None = None

    def to_jsonl(self) -> str:
        return json.dumps({"id": self.id, "parentId": self.parent_id,
                           "type": self.type, **self.data})

    @classmethod
    def from_dict(cls, d: dict) -> SessionEntry:
        entry_id = d.pop("id")
        parent_id = d.pop("parentId", None)
        entry_type = d.pop("type")
        return cls(id=entry_id, parent_id=parent_id, type=entry_type, data=d)


class SessionManager:
    VERSION = 3

    def __init__(self, sessions_dir: Path):
        self.sessions_dir = Path(sessions_dir)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self._session_id: str | None = None
        self._session_file: Path | None = None
        self._entries: list[SessionEntry] = []
        self._active_leaf_id: str | None = None

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def new_session(self, model: str) -> str:
        self._session_id = str(uuid.uuid4())
        self._session_file = self.sessions_dir / f"{self._session_id}.jsonl"
        self._entries = []
        self._active_leaf_id = None
        root = SessionEntry(
            type="session_info",
            data={"version": self.VERSION, "model": model,
                  "created_at": self._now()},
        )
        self._write_entry(root)
        return self._session_id

    def load_session(self, session_id: str) -> None:
        self._session_id = session_id
        self._session_file = self.sessions_dir / f"{session_id}.jsonl"
        self._entries = []
        with self._session_file.open() as f:
            for line in f:
                line = line.strip()
                if line:
                    d = json.loads(line)
                    self._entries.append(SessionEntry.from_dict(d))
        self._migrate_if_needed()
        # Default active leaf = last entry with no children
        leaf_ids = self.get_leaf_ids()
        self._active_leaf_id = leaf_ids[-1] if leaf_ids else self._entries[-1].id if self._entries else None

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def append(self, entry: SessionEntry) -> SessionEntry:
        entry.parent_id = self._active_leaf_id
        self._write_entry(entry)
        return entry

    def branch(self, from_entry_id: str) -> str:
        """Create new branch rooted at from_entry_id. Returns new active leaf id."""
        self._active_leaf_id = from_entry_id
        return from_entry_id

    def set_active_leaf(self, entry_id: str) -> None:
        self._active_leaf_id = entry_id

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def get_leaf_ids(self) -> list[str]:
        """Return all entry ids that have no children."""
        parent_ids = {e.parent_id for e in self._entries if e.parent_id}
        return [e.id for e in self._entries if e.id not in parent_ids]

    @property
    def current_leaf_id(self) -> str | None:
        return self._active_leaf_id

    def load_all_entries(self) -> list[SessionEntry]:
        return list(self._entries)

    def build_context(self, leaf_id: str | None = None) -> list[dict]:
        """Walk parent chain root→leaf. At CompactionEntry, discard prior messages."""
        leaf_id = leaf_id or self._active_leaf_id
        if not leaf_id:
            return []

        by_id = {e.id: e for e in self._entries}
        path: list[SessionEntry] = []
        current_id: str | None = leaf_id
        while current_id:
            entry = by_id.get(current_id)
            if entry is None:
                break
            path.append(entry)
            current_id = entry.parent_id
        path.reverse()  # root → leaf

        messages: list[dict] = []
        for entry in path:
            if entry.type == "compaction":
                messages = [{"role": "system", "content": f"[Context summary]: {entry.data.get('summary', '')}"}]
            elif entry.type == "message":
                role = entry.data.get("role", "user")
                content = entry.data.get("content", "")
                if role not in ("session_info",):
                    messages.append({"role": role, "content": content})
        return messages

    @staticmethod
    def list_sessions(sessions_dir: Path) -> list[str]:
        return [p.stem for p in Path(sessions_dir).glob("*.jsonl")]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _write_entry(self, entry: SessionEntry) -> None:
        self._entries.append(entry)
        self._active_leaf_id = entry.id
        with self._session_file.open("a") as f:
            f.write(entry.to_jsonl() + "\n")

    def _migrate_if_needed(self) -> None:
        if not self._entries:
            return
        first = self._entries[0]
        version = first.data.get("version", 1)
        if version < 2:
            self._migrate_v1_to_v2()
        if version < 3:
            self._migrate_v2_to_v3()

    def _migrate_v1_to_v2(self) -> None:
        """Add id/parentId tree structure."""
        prev_id = None
        for entry in self._entries:
            if entry.id is None or entry.id == "":
                entry.id = str(uuid.uuid4())
            entry.parent_id = prev_id
            prev_id = entry.id
        if self._entries:
            self._entries[0].data["version"] = 2
        self._rewrite_file()

    def _migrate_v2_to_v3(self) -> None:
        """Rename hookMessage → custom."""
        for entry in self._entries:
            if entry.type == "hookMessage":
                entry.type = "custom"
        if self._entries:
            self._entries[0].data["version"] = 3
        self._rewrite_file()

    def _rewrite_file(self) -> None:
        with self._session_file.open("w") as f:
            for entry in self._entries:
                f.write(entry.to_jsonl() + "\n")

    def _now(self) -> str:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/core/test_session_manager.py -v
```

Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add mypi/core/session_manager.py tests/core/test_session_manager.py
git commit -m "feat: implement JSONL tree session manager with branching"
```

---

## Task 6: Session Manager — Context Reconstruction + Compaction

**Files:**
- Modify: `tests/core/test_session_manager.py`

- [ ] **Step 1: Write the failing tests**

```python
# Append to tests/core/test_session_manager.py

def test_build_context_returns_messages_in_order(tmp_sessions_dir):
    sm = SessionManager(sessions_dir=tmp_sessions_dir)
    sm.new_session(model="gpt-4o")
    sm.append(SessionEntry(type="message", data={"role": "user", "content": "hello"}))
    sm.append(SessionEntry(type="message", data={"role": "assistant", "content": "world"}))
    ctx = sm.build_context()
    assert ctx == [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "world"},
    ]


def test_build_context_truncates_at_compaction(tmp_sessions_dir):
    sm = SessionManager(sessions_dir=tmp_sessions_dir)
    sm.new_session(model="gpt-4o")
    sm.append(SessionEntry(type="message", data={"role": "user", "content": "old message"}))
    sm.append(SessionEntry(type="compaction", data={"summary": "user said old message"}))
    sm.append(SessionEntry(type="message", data={"role": "user", "content": "new message"}))
    ctx = sm.build_context()
    # old message should be gone, replaced by compaction summary
    assert not any(m.get("content") == "old message" for m in ctx)
    assert any("user said old message" in m.get("content", "") for m in ctx)
    assert any(m.get("content") == "new message" for m in ctx)


def test_compaction_is_path_local(tmp_sessions_dir):
    sm = SessionManager(sessions_dir=tmp_sessions_dir)
    sm.new_session(model="gpt-4o")
    sm.append(SessionEntry(type="message", data={"role": "user", "content": "shared"}))
    branch_point = sm.current_leaf_id

    # Main branch: add compaction
    sm.append(SessionEntry(type="compaction", data={"summary": "main branch compacted"}))
    sm.append(SessionEntry(type="message", data={"role": "user", "content": "main continued"}))
    main_leaf = sm.current_leaf_id

    # Switch to branch from before compaction
    sm.branch(branch_point)
    sm.append(SessionEntry(type="message", data={"role": "user", "content": "side branch"}))
    side_leaf = sm.current_leaf_id

    # Side branch context should NOT be affected by main branch compaction
    side_ctx = sm.build_context(side_leaf)
    assert any(m.get("content") == "shared" for m in side_ctx)
    assert any(m.get("content") == "side branch" for m in side_ctx)
    assert not any("compacted" in m.get("content", "") for m in side_ctx)
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/core/test_session_manager.py::test_build_context_truncates_at_compaction -v
```

Expected: FAIL (context does not yet filter correctly for compaction).

- [ ] **Step 3: Verify implementation already passes**

The `build_context` implementation in Task 5 already handles compaction correctly. Run:

```bash
pytest tests/core/test_session_manager.py -v
```

Expected: All PASS. If any fail, fix `build_context` to ensure compaction resets `messages` list in the path traversal.

- [ ] **Step 4: Commit**

```bash
git add tests/core/test_session_manager.py
git commit -m "test: add context reconstruction and compaction path-locality tests"
```

---

## Task 7: Session Manager — Migration

**Files:**
- Modify: `tests/core/test_session_manager.py`

- [ ] **Step 1: Write the failing test**

```python
# Append to tests/core/test_session_manager.py
import json

def test_migrate_v1_to_v3(tmp_sessions_dir):
    """A v1 file (flat, no id/parentId) should be migrated to v3 on load."""
    session_id = "test-v1-session"
    v1_file = tmp_sessions_dir / f"{session_id}.jsonl"
    v1_file.write_text(
        json.dumps({"type": "session_info", "version": 1, "model": "gpt-3.5"}) + "\n" +
        json.dumps({"type": "hookMessage", "extension": "foo", "data": {}}) + "\n"
    )
    sm = SessionManager(sessions_dir=tmp_sessions_dir)
    sm.load_session(session_id)
    entries = sm.load_all_entries()
    assert entries[0].data.get("version") == 3
    assert entries[1].type == "custom"  # hookMessage → custom
    assert entries[0].id is not None
    assert entries[1].parent_id == entries[0].id
```

- [ ] **Step 2: Run to verify it fails**

```bash
pytest tests/core/test_session_manager.py::test_migrate_v1_to_v3 -v
```

Expected: FAIL.

- [ ] **Step 3: Fix migration** — ensure `_migrate_v1_to_v2` sets version to 2 before `_migrate_v2_to_v3` checks. Update `_migrate_if_needed`:

```python
def _migrate_if_needed(self) -> None:
    if not self._entries:
        return
    first = self._entries[0]
    version = first.data.get("version", 1)
    if version < 2:
        self._migrate_v1_to_v2()
        first.data["version"] = 2
    if version < 3:
        self._migrate_v2_to_v3()
        first.data["version"] = 3
```

- [ ] **Step 4: Run all session manager tests**

```bash
pytest tests/core/test_session_manager.py -v
```

Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add mypi/core/session_manager.py tests/core/test_session_manager.py
git commit -m "feat: add session migration v1→v2→v3"
```

---

## Task 8: Tools Base — Tool ABC, ToolResult, ToolRegistry, ExtensionRunner

**Files:**
- Modify: `mypi/tools/base.py` (replace the stub)
- Create: `tests/tools/test_base.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/tools/test_base.py
import pytest
from codepi.tools.base import Tool, ToolResult, ToolRegistry, ExtensionRunner
from codepi.core.events import ToolCallEvent, ToolResultEvent


class EchoTool(Tool):
    name = "echo"
    description = "Echoes input"
    input_schema = {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}

    async def execute(self, text: str) -> ToolResult:
        return ToolResult(output=text)


@pytest.mark.asyncio
async def test_tool_execute():
    tool = EchoTool()
    result = await tool.execute(text="hello")
    assert result.output == "hello"
    assert result.error is None


def test_registry_registers_tool():
    reg = ToolRegistry()
    reg.register(EchoTool())
    schema = reg.to_openai_schema()
    assert any(t["function"]["name"] == "echo" for t in schema)


@pytest.mark.asyncio
async def test_registry_wrap_intercepts_call():
    reg = ToolRegistry()
    tool = EchoTool()
    reg.register(tool)

    intercepted_calls = []

    class MockRunner:
        async def fire_tool_call(self, event: ToolCallEvent) -> ToolCallEvent:
            intercepted_calls.append(event)
            return event

        async def fire_tool_result(self, event: ToolResultEvent) -> ToolResultEvent:
            return event

    wrapped = reg.wrap(tool, MockRunner())
    result = await wrapped.execute(text="test")
    assert result.output == "test"
    assert len(intercepted_calls) == 1
    assert intercepted_calls[0].tool_name == "echo"
```

- [ ] **Step 2: Run to verify it fails**

```bash
pytest tests/tools/test_base.py -v
```

Expected: ImportError or AttributeError (stub doesn't have full implementation).

- [ ] **Step 3: Implement full `mypi/tools/base.py`**

```python
from __future__ import annotations
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable
from codepi.core.events import ToolCallEvent, ToolResultEvent


@dataclass
class ToolResult:
    output: str = ""
    error: str | None = None
    metadata: dict = field(default_factory=dict)

    def to_message_content(self) -> str:
        if self.error:
            return f"Error: {self.error}"
        return self.output


class Tool(ABC):
    name: str
    description: str
    input_schema: dict

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult: ...

    def to_openai_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema,
            },
        }


@runtime_checkable
class ExtensionRunner(Protocol):
    """Chains extension hooks for tool interception."""
    async def fire_tool_call(self, event: ToolCallEvent) -> ToolCallEvent: ...
    async def fire_tool_result(self, event: ToolResultEvent) -> ToolResultEvent: ...


class _WrappedTool(Tool):
    """Tool wrapped with extension interception."""

    def __init__(self, inner: Tool, runner: ExtensionRunner):
        self.name = inner.name
        self.description = inner.description
        self.input_schema = inner.input_schema
        self._inner = inner
        self._runner = runner

    async def execute(self, **kwargs) -> ToolResult:
        call_event = ToolCallEvent(tool_name=self.name, arguments=kwargs)
        call_event = await self._runner.fire_tool_call(call_event)
        result = await self._inner.execute(**call_event.arguments)
        result_event = ToolResultEvent(tool_name=self.name, result=result)
        result_event = await self._runner.fire_tool_result(result_event)
        return result_event.result


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def wrap(self, tool: Tool, runner: ExtensionRunner) -> Tool:
        wrapped = _WrappedTool(tool, runner)
        self._tools[tool.name] = wrapped
        return wrapped

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def to_openai_schema(self) -> list[dict]:
        return [t.to_openai_schema() for t in self._tools.values()]

    def all_tools(self) -> list[Tool]:
        return list(self._tools.values())
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/tools/test_base.py -v
```

Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add mypi/tools/base.py tests/tools/test_base.py
git commit -m "feat: implement Tool ABC, ToolRegistry, and ExtensionRunner protocol"
```

---

## Task 9: Built-in Tools — read, write, edit

**Files:**
- Create: `mypi/tools/builtins.py`
- Create: `tests/tools/test_builtins.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/tools/test_builtins.py
import pytest
from pathlib import Path
from codepi.tools.builtins import ReadTool, WriteTool, EditTool
from codepi.tools.base import ToolResult


@pytest.mark.asyncio
async def test_read_tool_reads_file(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("line1\nline2\nline3\n")
    tool = ReadTool()
    result = await tool.execute(path=str(f))
    assert "line1" in result.output
    assert "line2" in result.output


@pytest.mark.asyncio
async def test_read_tool_with_offset_and_limit(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("a\nb\nc\nd\ne\n")
    tool = ReadTool()
    result = await tool.execute(path=str(f), offset=2, limit=2)
    lines = result.output.strip().split("\n")
    assert len(lines) == 2
    assert "b" in result.output
    assert "a" not in result.output


@pytest.mark.asyncio
async def test_read_tool_missing_file():
    tool = ReadTool()
    result = await tool.execute(path="/nonexistent/file.py")
    assert result.error is not None


@pytest.mark.asyncio
async def test_write_tool_creates_file(tmp_path):
    f = tmp_path / "new.txt"
    tool = WriteTool()
    result = await tool.execute(path=str(f), content="hello world")
    assert result.error is None
    assert f.read_text() == "hello world"


@pytest.mark.asyncio
async def test_edit_tool_replaces_string(tmp_path):
    f = tmp_path / "edit.py"
    f.write_text("def foo():\n    return 1\n")
    tool = EditTool()
    result = await tool.execute(path=str(f), old_string="return 1", new_string="return 42")
    assert result.error is None
    assert "return 42" in f.read_text()


@pytest.mark.asyncio
async def test_edit_tool_fails_if_not_unique(tmp_path):
    f = tmp_path / "dupe.py"
    f.write_text("x = 1\nx = 1\n")
    tool = EditTool()
    result = await tool.execute(path=str(f), old_string="x = 1", new_string="x = 2")
    assert result.error is not None
    assert "not unique" in result.error


@pytest.mark.asyncio
async def test_edit_tool_fails_if_not_found(tmp_path):
    f = tmp_path / "notfound.py"
    f.write_text("x = 1\n")
    tool = EditTool()
    result = await tool.execute(path=str(f), old_string="y = 99", new_string="y = 0")
    assert result.error is not None
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/tools/test_builtins.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement read, write, edit in `mypi/tools/builtins.py`**

```python
from __future__ import annotations
import asyncio
import json
from pathlib import Path
from codepi.tools.base import Tool, ToolResult


class ReadTool(Tool):
    name = "read"
    description = "Read a file's contents. Optional offset (1-based line number to start from) and limit (max lines to return)."
    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Absolute or relative file path"},
            "offset": {"type": "integer", "description": "1-based line to start reading from"},
            "limit": {"type": "integer", "description": "Maximum number of lines to return"},
        },
        "required": ["path"],
    }

    async def execute(self, path: str, offset: int = 1, limit: int | None = None) -> ToolResult:
        try:
            lines = Path(path).read_text().splitlines()
            start = max(0, offset - 1)
            end = start + limit if limit else len(lines)
            selected = lines[start:end]
            return ToolResult(output="\n".join(selected))
        except FileNotFoundError:
            return ToolResult(error=f"File not found: {path}")
        except Exception as e:
            return ToolResult(error=str(e))


class WriteTool(Tool):
    name = "write"
    description = "Write content to a file, creating or overwriting it."
    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "content": {"type": "string"},
        },
        "required": ["path", "content"],
    }

    async def execute(self, path: str, content: str) -> ToolResult:
        try:
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content)
            return ToolResult(output=f"Written {len(content)} bytes to {path}")
        except Exception as e:
            return ToolResult(error=str(e))


class EditTool(Tool):
    name = "edit"
    description = "Replace old_string with new_string in a file. Fails if old_string appears 0 or 2+ times."
    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "old_string": {"type": "string"},
            "new_string": {"type": "string"},
        },
        "required": ["path", "old_string", "new_string"],
    }

    async def execute(self, path: str, old_string: str, new_string: str) -> ToolResult:
        try:
            content = Path(path).read_text()
            count = content.count(old_string)
            if count == 0:
                return ToolResult(error=f"old_string not found in {path}")
            if count > 1:
                return ToolResult(error=f"old_string is not unique in {path} ({count} occurrences)")
            new_content = content.replace(old_string, new_string, 1)
            Path(path).write_text(new_content)
            return ToolResult(output=f"Replaced 1 occurrence in {path}")
        except FileNotFoundError:
            return ToolResult(error=f"File not found: {path}")
        except Exception as e:
            return ToolResult(error=str(e))
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/tools/test_builtins.py -k "read or write or edit" -v
```

Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add mypi/tools/builtins.py tests/tools/test_builtins.py
git commit -m "feat: implement read, write, edit built-in tools"
```

---

## Task 10: Built-in Tools — bash, find, grep, ls

**Files:**
- Modify: `mypi/tools/builtins.py`
- Modify: `tests/tools/test_builtins.py`

- [ ] **Step 1: Write the failing tests**

```python
# Append to tests/tools/test_builtins.py
from codepi.tools.builtins import BashTool, FindTool, GrepTool, LsTool


@pytest.mark.asyncio
async def test_bash_tool_runs_command():
    tool = BashTool()
    result = await tool.execute(command="echo hello")
    assert "hello" in result.output
    assert result.error is None


@pytest.mark.asyncio
async def test_bash_tool_captures_stderr():
    tool = BashTool()
    result = await tool.execute(command="echo err >&2; exit 1")
    assert result.error is not None or "err" in result.output


@pytest.mark.asyncio
async def test_bash_tool_timeout(tmp_path):
    tool = BashTool()
    result = await tool.execute(command="sleep 10", timeout=1)
    assert result.error is not None
    assert "timeout" in result.error.lower()


@pytest.mark.asyncio
async def test_find_tool_finds_files(tmp_path):
    (tmp_path / "a.py").write_text("x")
    (tmp_path / "b.txt").write_text("y")
    tool = FindTool()
    result = await tool.execute(path=str(tmp_path), pattern="*.py")
    assert "a.py" in result.output
    assert "b.txt" not in result.output


@pytest.mark.asyncio
async def test_grep_tool_finds_pattern(tmp_path):
    (tmp_path / "source.py").write_text("def hello():\n    return 42\n")
    tool = GrepTool()
    result = await tool.execute(pattern="def hello", path=str(tmp_path))
    assert "source.py" in result.output


@pytest.mark.asyncio
async def test_ls_tool_lists_directory(tmp_path):
    (tmp_path / "foo.txt").write_text("hi")
    (tmp_path / "bar.py").write_text("x")
    tool = LsTool()
    result = await tool.execute(path=str(tmp_path))
    assert "foo.txt" in result.output
    assert "bar.py" in result.output
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/tools/test_builtins.py -k "bash or find or grep or ls" -v
```

Expected: ImportError on new tools.

- [ ] **Step 3: Add bash, find, grep, ls to `mypi/tools/builtins.py`**

```python
# Append to mypi/tools/builtins.py
import asyncio
import fnmatch
import os
import re
import shutil
import subprocess
from datetime import datetime


class BashTool(Tool):
    name = "bash"
    description = "Execute a shell command. Returns stdout. Use timeout to prevent hanging."
    input_schema = {
        "type": "object",
        "properties": {
            "command": {"type": "string"},
            "timeout": {"type": "number", "description": "Seconds before killing the command (default 30)"},
        },
        "required": ["command"],
    }

    async def execute(self, command: str, timeout: float = 30) -> ToolResult:
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            try:
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            except asyncio.TimeoutError:
                proc.kill()
                return ToolResult(error=f"Command timed out after {timeout}s")
            output = stdout.decode(errors="replace")
            if proc.returncode != 0:
                return ToolResult(output=output, error=f"Exit code {proc.returncode}: {output.strip()[:200]}")
            return ToolResult(output=output)
        except Exception as e:
            return ToolResult(error=str(e))


class FindTool(Tool):
    name = "find"
    description = "Find files matching a glob pattern, sorted by modification time (newest first)."
    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Directory to search in"},
            "pattern": {"type": "string", "description": "Glob pattern, e.g. '*.py'"},
        },
        "required": ["path", "pattern"],
    }

    async def execute(self, path: str, pattern: str) -> ToolResult:
        try:
            matches = sorted(
                Path(path).rglob(pattern),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            return ToolResult(output="\n".join(str(m) for m in matches))
        except Exception as e:
            return ToolResult(error=str(e))


class GrepTool(Tool):
    name = "grep"
    description = "Search file contents for a regex pattern. Uses ripgrep if available, falls back to Python re."
    input_schema = {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Regex pattern"},
            "path": {"type": "string", "description": "Directory or file to search"},
            "glob": {"type": "string", "description": "File glob filter, e.g. '*.py'"},
        },
        "required": ["pattern", "path"],
    }

    async def execute(self, pattern: str, path: str, glob: str | None = None) -> ToolResult:
        if shutil.which("rg"):
            return await self._rg(pattern, path, glob)
        return await self._python_grep(pattern, path, glob)

    async def _rg(self, pattern: str, path: str, glob: str | None) -> ToolResult:
        cmd = ["rg", "--line-number", pattern, path]
        if glob:
            cmd += ["--glob", glob]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
            if proc.returncode not in (0, 1):
                return ToolResult(error=stderr.decode(errors="replace"))
            return ToolResult(output=stdout.decode(errors="replace"))
        except Exception as e:
            return ToolResult(error=str(e))

    async def _python_grep(self, pattern: str, path: str, glob: str | None) -> ToolResult:
        try:
            rx = re.compile(pattern)
            results = []
            search_path = Path(path)
            files = search_path.rglob(glob or "*") if search_path.is_dir() else [search_path]
            for f in files:
                if not f.is_file():
                    continue
                try:
                    for i, line in enumerate(f.read_text(errors="replace").splitlines(), 1):
                        if rx.search(line):
                            results.append(f"{f}:{i}: {line}")
                except Exception:
                    pass
            return ToolResult(output="\n".join(results))
        except re.error as e:
            return ToolResult(error=f"Invalid regex: {e}")


class LsTool(Tool):
    name = "ls"
    description = "List directory contents with file metadata."
    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Directory to list"},
        },
        "required": ["path"],
    }

    async def execute(self, path: str) -> ToolResult:
        try:
            entries = []
            for p in sorted(Path(path).iterdir()):
                stat = p.stat()
                kind = "dir" if p.is_dir() else "file"
                size = stat.st_size
                mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
                entries.append(f"{kind:4}  {size:>8}  {mtime}  {p.name}")
            return ToolResult(output="\n".join(entries))
        except Exception as e:
            return ToolResult(error=str(e))


def make_builtin_registry() -> "ToolRegistry":
    """Create a ToolRegistry pre-populated with all 7 built-in tools."""
    from codepi.tools.base import ToolRegistry
    reg = ToolRegistry()
    for tool in [ReadTool(), WriteTool(), EditTool(), BashTool(), FindTool(), GrepTool(), LsTool()]:
        reg.register(tool)
    return reg
```

- [ ] **Step 4: Run all tool tests**

```bash
pytest tests/tools/ -v
```

Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add mypi/tools/builtins.py tests/tools/test_builtins.py
git commit -m "feat: implement bash, find, grep, ls built-in tools"
```

---

## Task 11: Extension Base — ABC + UIComponents

**Files:**
- Create: `mypi/extensions/base.py`
- Create: `tests/extensions/test_base.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/extensions/test_base.py
import pytest
from codepi.extensions.base import Extension, UIComponents
from codepi.core.events import (
    BeforeAgentStartEvent, ToolCallEvent, ToolResultEvent,
    SessionForkEvent, SessionTreeEvent
)
from codepi.tools.base import ToolResult


class NullExtension(Extension):
    name = "null"


@pytest.mark.asyncio
async def test_extension_default_hooks_are_noop():
    ext = NullExtension()
    evt = BeforeAgentStartEvent(system_prompt="x", messages=[])
    result = await ext.on_before_agent_start(evt)
    assert result is None  # default noop


@pytest.mark.asyncio
async def test_extension_can_modify_system_prompt():
    class InjectExtension(Extension):
        name = "inject"
        async def on_before_agent_start(self, event: BeforeAgentStartEvent):
            return BeforeAgentStartEvent(
                system_prompt=event.system_prompt + "\ninjected",
                messages=event.messages
            )

    ext = InjectExtension()
    evt = BeforeAgentStartEvent(system_prompt="base", messages=[])
    result = await ext.on_before_agent_start(evt)
    assert result is not None
    assert "injected" in result.system_prompt


def test_ui_components_defaults():
    ui = UIComponents()
    assert ui.header is None
    assert ui.footer is None
    assert ui.widgets == {}


def test_extension_returns_no_tools_by_default():
    ext = NullExtension()
    assert ext.get_tools() == []
```

- [ ] **Step 2: Run to verify it fails**

```bash
pytest tests/extensions/test_base.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `mypi/extensions/base.py`**

```python
from __future__ import annotations
from abc import ABC
from dataclasses import dataclass, field
from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from codepi.core.events import (
        BeforeAgentStartEvent, BeforeProviderRequestEvent,
        ToolCallEvent, ToolResultEvent, SessionForkEvent, SessionTreeEvent
    )
    from codepi.tools.base import Tool


@dataclass
class UIComponents:
    header: Callable[[], str] | None = None
    footer: Callable[[], str] | None = None
    widgets: dict[str, Callable[[], str]] = field(default_factory=dict)


class Extension(ABC):
    name: str

    # Mutable hooks — return modified event or None (no-op, keep original)
    async def on_before_agent_start(self, event: "BeforeAgentStartEvent") -> "BeforeAgentStartEvent | None":
        return None

    async def on_before_provider_request(self, event: "BeforeProviderRequestEvent") -> "BeforeProviderRequestEvent | None":
        return None

    async def on_tool_call(self, event: "ToolCallEvent") -> "ToolCallEvent | None":
        return None

    async def on_tool_result(self, event: "ToolResultEvent") -> "ToolResultEvent | None":
        return None

    # Notification hooks — observation only
    async def on_session_fork(self, event: "SessionForkEvent") -> None:
        pass

    async def on_session_tree(self, event: "SessionTreeEvent") -> None:
        pass

    # Registration
    def get_tools(self) -> list["Tool"]:
        return []

    def get_shortcuts(self) -> dict[str, Callable]:
        return {}

    def get_ui_components(self) -> UIComponents | None:
        return None
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/extensions/test_base.py -v
```

Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add mypi/extensions/base.py tests/extensions/test_base.py
git commit -m "feat: implement Extension ABC and UIComponents"
```

---

## Task 12: Skill Loader

**Files:**
- Create: `mypi/extensions/skill_loader.py`
- Create: `tests/extensions/test_skill_loader.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/extensions/test_skill_loader.py
import pytest
from pathlib import Path
from codepi.extensions.skill_loader import SkillLoader
from codepi.core.events import BeforeAgentStartEvent


def write_skill(skills_dir: Path, name: str, content: str):
    (skills_dir / f"{name}.md").write_text(content)


@pytest.fixture
def skill_with_frontmatter(tmp_skills_dir):
    write_skill(tmp_skills_dir, "my-skill", """---
name: my-skill
description: Use when the user asks about Python.
---

## My Skill

Always use type hints.
""")
    return tmp_skills_dir


def test_skill_loader_injects_into_system_prompt(skill_with_frontmatter):
    loader = SkillLoader(skills_dirs=[skill_with_frontmatter])
    evt = BeforeAgentStartEvent(system_prompt="Base prompt.", messages=[])
    modified = loader.inject_skills(evt)
    assert "my-skill" in modified.system_prompt
    assert "Always use type hints" in modified.system_prompt


def test_skill_loader_ignores_invalid_frontmatter(tmp_skills_dir):
    write_skill(tmp_skills_dir, "bad-skill", "No frontmatter here.")
    loader = SkillLoader(skills_dirs=[tmp_skills_dir])
    evt = BeforeAgentStartEvent(system_prompt="Base.", messages=[])
    modified = loader.inject_skills(evt)
    # Should not crash, may or may not inject (graceful)
    assert modified is not None


def test_skill_loader_scans_multiple_dirs(tmp_path):
    dir1 = tmp_path / "d1"
    dir2 = tmp_path / "d2"
    dir1.mkdir(); dir2.mkdir()
    write_skill(dir1, "skill-a", "---\nname: skill-a\ndescription: A.\n---\nContent A")
    write_skill(dir2, "skill-b", "---\nname: skill-b\ndescription: B.\n---\nContent B")
    loader = SkillLoader(skills_dirs=[dir1, dir2])
    evt = BeforeAgentStartEvent(system_prompt="", messages=[])
    modified = loader.inject_skills(evt)
    assert "Content A" in modified.system_prompt
    assert "Content B" in modified.system_prompt
```

- [ ] **Step 2: Run to verify it fails**

```bash
pytest tests/extensions/test_skill_loader.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `mypi/extensions/skill_loader.py`**

```python
from __future__ import annotations
from pathlib import Path
import yaml
from codepi.core.events import BeforeAgentStartEvent


def _parse_skill(path: Path) -> dict | None:
    """Parse a Claude Code–format skill .md file. Returns dict with name, description, body."""
    text = path.read_text()
    if not text.startswith("---"):
        return None
    try:
        end = text.index("---", 3)
        frontmatter = yaml.safe_load(text[3:end])
        body = text[end + 3:].strip()
        if not isinstance(frontmatter, dict) or "name" not in frontmatter:
            return None
        return {"name": frontmatter["name"], "description": frontmatter.get("description", ""),
                "compatibility": frontmatter.get("compatibility"), "body": body}
    except Exception:
        return None


class SkillLoader:
    def __init__(self, skills_dirs: list[Path]):
        self.skills_dirs = [Path(d) for d in skills_dirs]

    def load_skills(self) -> list[dict]:
        skills = []
        for d in self.skills_dirs:
            if not d.exists():
                continue
            for md_file in sorted(d.glob("*.md")):
                skill = _parse_skill(md_file)
                if skill:
                    skills.append(skill)
        return skills

    def inject_skills(self, event: BeforeAgentStartEvent) -> BeforeAgentStartEvent:
        skills = self.load_skills()
        if not skills:
            return event
        injected = "\n\n".join(
            f"## Skill: {s['name']}\n**When to use:** {s['description']}\n\n{s['body']}"
            for s in skills
        )
        new_prompt = event.system_prompt.rstrip() + "\n\n---\n# Available Skills\n\n" + injected
        return BeforeAgentStartEvent(system_prompt=new_prompt, messages=event.messages)
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/extensions/test_skill_loader.py -v
```

Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add mypi/extensions/skill_loader.py tests/extensions/test_skill_loader.py
git commit -m "feat: implement Claude Code–compatible skill loader"
```

---

## Task 13: Extension Loader + Hot-Reload

**Files:**
- Create: `mypi/extensions/loader.py`
- Create: `tests/extensions/test_loader.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/extensions/test_loader.py
import pytest
import time
from pathlib import Path
from codepi.extensions.base import Extension
from codepi.extensions.loader import ExtensionLoader


@pytest.fixture
def simple_extension_file(tmp_extensions_dir):
    ext_file = tmp_extensions_dir / "my_ext.py"
    ext_file.write_text("""
from codepi.extensions.base import Extension

class MyExtension(Extension):
    name = "my-extension"
""")
    return ext_file


def test_loader_finds_extension_subclasses(simple_extension_file, tmp_extensions_dir):
    loader = ExtensionLoader(extensions_dir=tmp_extensions_dir)
    loader.load()
    names = [e.name for e in loader.extensions]
    assert "my-extension" in names


def test_loader_ignores_non_extension_files(tmp_extensions_dir):
    (tmp_extensions_dir / "utils.py").write_text("x = 1")
    loader = ExtensionLoader(extensions_dir=tmp_extensions_dir)
    loader.load()
    assert loader.extensions == []


def test_loader_isolates_broken_extension(tmp_extensions_dir):
    (tmp_extensions_dir / "broken.py").write_text("raise ValueError('intentional')")
    loader = ExtensionLoader(extensions_dir=tmp_extensions_dir)
    loader.load()  # Should not raise
    assert loader.extensions == []
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/extensions/test_loader.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `mypi/extensions/loader.py`**

```python
from __future__ import annotations
import importlib.util
import inspect
import logging
import sys
from pathlib import Path
from codepi.extensions.base import Extension

logger = logging.getLogger(__name__)


class ExtensionLoader:
    def __init__(self, extensions_dir: Path):
        self.extensions_dir = Path(extensions_dir)
        self.extensions: list[Extension] = []
        self._observer = None

    def load(self) -> list[Extension]:
        """Scan extensions_dir for .py files, import, instantiate Extension subclasses."""
        self.extensions = []
        if not self.extensions_dir.exists():
            return []
        for py_file in sorted(self.extensions_dir.glob("*.py")):
            self._load_file(py_file)
        return self.extensions

    def start_watching(self, on_idle: "Callable[[], bool]") -> None:
        """Start watchdog observer. Hot-reload is deferred until on_idle() returns True."""
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler

            loader = self

            class Handler(FileSystemEventHandler):
                def on_modified(self, event):
                    if event.src_path.endswith(".py"):
                        if on_idle():
                            logger.info(f"Hot-reloading extensions (triggered by {event.src_path})")
                            loader.load()

            self._observer = Observer()
            self._observer.schedule(Handler(), str(self.extensions_dir), recursive=False)
            self._observer.start()
        except ImportError:
            logger.warning("watchdog not installed — hot-reload disabled")

    def stop_watching(self) -> None:
        if self._observer:
            self._observer.stop()
            self._observer.join()

    def _load_file(self, path: Path) -> None:
        module_name = f"mypi_ext_{path.stem}"
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            return
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            logger.error(f"Failed to load extension {path.name}: {e}")
            return
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if (issubclass(obj, Extension) and obj is not Extension
                    and not inspect.isabstract(obj)):
                try:
                    instance = obj()
                    self.extensions.append(instance)
                    logger.info(f"Loaded extension: {instance.name}")
                except Exception as e:
                    logger.error(f"Failed to instantiate {obj.__name__}: {e}")
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/extensions/test_loader.py -v
```

Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add mypi/extensions/loader.py tests/extensions/test_loader.py
git commit -m "feat: implement extension loader with hot-reload via watchdog"
```

---

## Task 14: AgentSession — Core Loop

**Files:**
- Create: `mypi/core/agent_session.py`
- Create: `tests/core/test_agent_session.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/core/test_agent_session.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from codepi.core.agent_session import AgentSession
from codepi.ai.provider import TokenEvent, LLMToolCallEvent, DoneEvent, TokenUsage
from codepi.core.session_manager import SessionManager
from codepi.tools.builtins import make_builtin_registry


def make_mock_provider(events):
    """Create a mock LLMProvider that yields the given events."""
    async def stream(*args, **kwargs):
        for e in events:
            yield e
    provider = MagicMock()
    provider.stream = stream
    return provider


@pytest.mark.asyncio
async def test_prompt_fires_token_events(tmp_sessions_dir):
    events = [TokenEvent(text="Hello"), TokenEvent(text=" world"), DoneEvent(usage=TokenUsage(10, 5))]
    provider = make_mock_provider(events)
    sm = SessionManager(tmp_sessions_dir)
    sm.new_session(model="gpt-4o")
    session = AgentSession(provider=provider, session_manager=sm, model="gpt-4o")

    received_tokens = []
    session.on_token = lambda t: received_tokens.append(t)

    await session.prompt("say hello")
    assert received_tokens == ["Hello", " world"]


@pytest.mark.asyncio
async def test_prompt_executes_tool_calls(tmp_sessions_dir):
    tool_events = [
        LLMToolCallEvent(id="c1", name="echo", arguments={"text": "from tool"}),
        DoneEvent(usage=TokenUsage(10, 5)),
    ]
    provider = make_mock_provider(tool_events)
    sm = SessionManager(tmp_sessions_dir)
    sm.new_session(model="gpt-4o")

    from codepi.tools.base import Tool, ToolResult, ToolRegistry
    class EchoTool(Tool):
        name = "echo"
        description = "echo"
        input_schema = {"type": "object", "properties": {"text": {"type": "string"}}}
        async def execute(self, text=""):
            return ToolResult(output=text)

    registry = ToolRegistry()
    registry.register(EchoTool())
    session = AgentSession(provider=provider, session_manager=sm, model="gpt-4o", tool_registry=registry)

    tool_results = []
    session.on_tool_result = lambda name, result: tool_results.append((name, result))

    await session.prompt("use echo")
    assert any(r[0] == "echo" and r[1].output == "from tool" for r in tool_results)


@pytest.mark.asyncio
async def test_prompt_stores_messages_in_session(tmp_sessions_dir):
    events = [TokenEvent(text="Hi"), DoneEvent(usage=TokenUsage(5, 3))]
    provider = make_mock_provider(events)
    sm = SessionManager(tmp_sessions_dir)
    sm.new_session(model="gpt-4o")
    session = AgentSession(provider=provider, session_manager=sm, model="gpt-4o")

    await session.prompt("hello")
    ctx = sm.build_context()
    assert any(m.get("content") == "hello" for m in ctx)
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/core/test_agent_session.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `mypi/core/agent_session.py`**

```python
from __future__ import annotations
import asyncio
import logging
from typing import Callable
from codepi.ai.provider import LLMProvider, TokenEvent, LLMToolCallEvent, DoneEvent
from codepi.core.events import (
    BeforeAgentStartEvent, BeforeProviderRequestEvent,
    ToolCallEvent, ToolResultEvent, TokenStreamEvent,
    AutoRetryStartEvent, AutoRetryEndEvent,
    AutoCompactionStartEvent, AutoCompactionEndEvent,
)
from codepi.core.session_manager import SessionManager, SessionEntry
from codepi.extensions.base import Extension
from codepi.tools.base import ToolRegistry, ToolResult

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = "You are a helpful coding assistant. Use the available tools to help the user."


class AgentSession:
    def __init__(
        self,
        provider: LLMProvider,
        session_manager: SessionManager,
        model: str,
        tool_registry: ToolRegistry | None = None,
        extensions: list[Extension] | None = None,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        compaction_threshold: float = 0.80,
        max_retries: int = 3,
    ):
        self.provider = provider
        self.session_manager = session_manager
        self.model = model
        self.tool_registry = tool_registry or ToolRegistry()
        self.extensions = extensions or []
        self.system_prompt = system_prompt
        self.compaction_threshold = compaction_threshold
        self.max_retries = max_retries
        self._is_idle = True
        self._in_flight_tool: str | None = None   # name of currently executing tool, or None
        self._steer_override: str | None = None   # set by steer() when tool is in-flight

        # Simple callbacks for callers (modes) to receive events
        self.on_token: Callable[[str], None] | None = None
        self.on_tool_call: Callable[[str, dict], None] | None = None
        self.on_tool_result: Callable[[str, ToolResult], None] | None = None
        self.on_error: Callable[[str], None] | None = None

    @property
    def is_idle(self) -> bool:
        return self._is_idle

    async def prompt(self, text: str) -> None:
        self._is_idle = False
        try:
            self.session_manager.append(SessionEntry(type="message", data={"role": "user", "content": text}))
            await self._run_turn()
        finally:
            self._is_idle = True

    async def steer(self, text: str) -> None:
        """Inject a correction. If a tool call is in-flight, replaces its result.
        If no tool call is active, degrades to follow_up (queued as role: "user")."""
        if not self._is_idle and self._in_flight_tool:
            # Replace the pending tool result with steered text
            self._steer_override = text
        else:
            # Degrade to follow_up — stored as role: "user"
            await self.follow_up(text)

    async def follow_up(self, text: str) -> None:
        await self.prompt(text)

    async def _run_turn(self) -> None:
        # Fire BeforeAgentStartEvent
        evt = BeforeAgentStartEvent(
            system_prompt=self.system_prompt,
            messages=self.session_manager.build_context(),
        )
        for ext in self.extensions:
            result = await ext.on_before_agent_start(evt)
            if result is not None:
                evt = result

        # Fire BeforeProviderRequestEvent
        params_evt = BeforeProviderRequestEvent(params={})
        for ext in self.extensions:
            result = await ext.on_before_provider_request(params_evt)
            if result is not None:
                params_evt = result

        for attempt in range(1, self.max_retries + 1):
            try:
                await self._stream_turn(evt, params_evt)
                return
            except Exception as e:
                if attempt < self.max_retries:
                    delay = 2 ** attempt
                    logger.warning(f"API error (attempt {attempt}): {e}. Retrying in {delay}s")
                    await asyncio.sleep(delay)
                else:
                    if self.on_error:
                        self.on_error(f"Failed after {self.max_retries} attempts: {e}")
                    raise

    async def _stream_turn(self, start_evt: BeforeAgentStartEvent, params_evt: BeforeProviderRequestEvent) -> None:
        assistant_content = []
        tool_calls_made = []

        async for event in self.provider.stream(
            messages=start_evt.messages,
            tools=self.tool_registry.to_openai_schema(),
            model=self.model,
            system=start_evt.system_prompt,
            **params_evt.params,
        ):
            if isinstance(event, TokenEvent):
                assistant_content.append(event.text)
                if self.on_token:
                    self.on_token(event.text)

            elif isinstance(event, LLMToolCallEvent):
                # Fire extension ToolCallEvent (interceptable)
                call_evt = ToolCallEvent(tool_name=event.name, arguments=event.arguments)
                for ext in self.extensions:
                    result = await ext.on_tool_call(call_evt)
                    if result is not None:
                        call_evt = result

                if self.on_tool_call:
                    self.on_tool_call(call_evt.tool_name, call_evt.arguments)

                self._in_flight_tool = call_evt.tool_name
                self._steer_override = None

                tool = self.tool_registry.get(call_evt.tool_name)
                if tool:
                    tool_result = await tool.execute(**call_evt.arguments)
                else:
                    tool_result = ToolResult(error=f"Unknown tool: {call_evt.tool_name}")

                # steer() may have set an override while the tool was running
                if self._steer_override is not None:
                    tool_result = ToolResult(output=self._steer_override)
                    self._steer_override = None

                self._in_flight_tool = None

                # Fire extension ToolResultEvent (interceptable)
                result_evt = ToolResultEvent(tool_name=call_evt.tool_name, result=tool_result)
                for ext in self.extensions:
                    r = await ext.on_tool_result(result_evt)
                    if r is not None:
                        result_evt = r

                if self.on_tool_result:
                    self.on_tool_result(result_evt.tool_name, result_evt.result)

                tool_calls_made.append({
                    "id": event.id,
                    "name": result_evt.tool_name,
                    "result": result_evt.result.to_message_content(),
                })

            elif isinstance(event, DoneEvent):
                pass  # token usage available if needed

        # Persist assistant message
        if assistant_content:
            self.session_manager.append(SessionEntry(
                type="message",
                data={"role": "assistant", "content": "".join(assistant_content)},
            ))
        for tc in tool_calls_made:
            self.session_manager.append(SessionEntry(
                type="message",
                data={"role": "tool", "tool_call_id": tc["id"],
                      "name": tc["name"], "content": tc["result"]},
            ))
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/core/test_agent_session.py -v
```

Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add mypi/core/agent_session.py tests/core/test_agent_session.py
git commit -m "feat: implement AgentSession core loop with tool dispatch and extension hooks"
```

---

## Task 15: AgentSession — Retry + Compaction

**Files:**
- Modify: `tests/core/test_agent_session.py`
- Modify: `mypi/core/agent_session.py`

- [ ] **Step 1: Write the failing tests**

```python
# Append to tests/core/test_agent_session.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_prompt_retries_on_api_error(tmp_sessions_dir):
    call_count = 0

    async def flaky_stream(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise Exception("server error")
        yield TokenEvent(text="ok")
        yield DoneEvent(usage=TokenUsage(5, 3))

    provider = MagicMock()
    provider.stream = flaky_stream
    sm = SessionManager(tmp_sessions_dir)
    sm.new_session(model="gpt-4o")
    session = AgentSession(provider=provider, session_manager=sm, model="gpt-4o", max_retries=3)

    # Patch asyncio.sleep to avoid waiting
    with patch("asyncio.sleep", new_callable=AsyncMock):
        await session.prompt("test")

    assert call_count == 3


@pytest.mark.asyncio
async def test_prompt_raises_after_max_retries(tmp_sessions_dir):
    async def always_fail(*args, **kwargs):
        raise Exception("always fails")
        yield  # make it an async generator

    provider = MagicMock()
    provider.stream = always_fail
    sm = SessionManager(tmp_sessions_dir)
    sm.new_session(model="gpt-4o")
    session = AgentSession(provider=provider, session_manager=sm, model="gpt-4o", max_retries=2)

    with patch("asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(Exception, match="always fails"):
            await session.prompt("fail")
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/core/test_agent_session.py::test_prompt_retries_on_api_error -v
```

Expected: FAIL (retry logic not working with async generators).

- [ ] **Step 3: Verify `_run_turn` handles retries correctly**

The Task 14 implementation already loops `for attempt in range(1, self.max_retries + 1)` and calls `_stream_turn(...)` as a fresh coroutine each iteration. If the test fails with "TypeError: object async_generator can't be used in 'await' expression", it means `_stream_turn` was accidentally written as an `async def` that `yield`s instead of a regular coroutine. Verify `_stream_turn` uses `async for event in self.provider.stream(...)` internally (consuming the generator) and does not itself yield. If the test still fails, add this explicit check to `_run_turn`:

```python
except Exception as e:
    if attempt >= self.max_retries:
        if self.on_error:
            self.on_error(f"Failed after {self.max_retries} attempts: {e}")
        raise
    delay = 2 ** attempt
    logger.warning(f"Retrying (attempt {attempt}/{self.max_retries}) after {delay}s: {e}")
    await asyncio.sleep(delay)
```

- [ ] **Step 4: Add auto-compaction to `AgentSession._stream_turn`**

Add `_total_input_tokens` and `_context_window` tracking to `__init__`:

```python
self._total_input_tokens: int = 0
self._context_window: int = 128_000  # conservative default; override via kwargs
```

After processing `DoneEvent`, check compaction threshold and summarize if needed. Add this to `_stream_turn` after the `elif isinstance(event, DoneEvent):` branch:

```python
elif isinstance(event, DoneEvent):
    self._total_input_tokens = event.usage.input_tokens
    # Check if we've exceeded compaction threshold
    if self._total_input_tokens > self._context_window * self.compaction_threshold:
        await self._run_auto_compaction()
```

Add `_run_auto_compaction` to `AgentSession`:

```python
async def _run_auto_compaction(self) -> None:
    """Summarize current context and store a CompactionEntry."""
    from codepi.core.session_manager import SessionEntry
    context = self.session_manager.build_context()
    if not context:
        return
    summary_prompt = [
        *context,
        {"role": "user", "content":
         "Please summarize the conversation so far in a concise paragraph, "
         "preserving all key decisions, file names, and code changes discussed."}
    ]
    summary_parts: list[str] = []
    async for event in self.provider.stream(
        messages=summary_prompt, tools=[], model=self.model, system=""
    ):
        from codepi.ai.provider import TokenEvent
        if isinstance(event, TokenEvent):
            summary_parts.append(event.text)
    summary = "".join(summary_parts)
    self.session_manager.append(SessionEntry(
        type="compaction", data={"summary": summary}
    ))
```

- [ ] **Step 5: Write compaction test**

```python
# Append to tests/core/test_agent_session.py
@pytest.mark.asyncio
async def test_compaction_runs_when_threshold_exceeded(tmp_sessions_dir):
    """When DoneEvent reports token usage > threshold, auto-compaction should fire."""
    # First call: main turn returning high token usage
    # Second call: compaction summarization turn
    call_count = 0

    async def provider_stream(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            yield TokenEvent(text="answer")
            # Report usage above 80% of 128k default
            yield DoneEvent(usage=TokenUsage(input_tokens=110_000, output_tokens=500))
        else:
            # Compaction summary turn
            yield TokenEvent(text="Summary of prior context.")
            yield DoneEvent(usage=TokenUsage(input_tokens=1000, output_tokens=100))

    provider = MagicMock()
    provider.stream = provider_stream
    sm = SessionManager(tmp_sessions_dir)
    sm.new_session(model="gpt-4o")
    session = AgentSession(provider=provider, session_manager=sm, model="gpt-4o",
                           compaction_threshold=0.80)

    await session.prompt("heavy request")

    # Verify a compaction entry was written
    entries = sm.load_all_entries()
    compaction_entries = [e for e in entries if e.type == "compaction"]
    assert len(compaction_entries) == 1
    assert "Summary" in compaction_entries[0].data.get("summary", "")
```

- [ ] **Step 6: Run to verify compaction test passes**

```bash
pytest tests/core/test_agent_session.py::test_compaction_runs_when_threshold_exceeded -v
```

Expected: PASS.

- [ ] **Step 7: Run all session tests**

```bash
pytest tests/core/ -v
```

Expected: All PASS.

- [ ] **Step 8: Commit**

```bash
git add mypi/core/agent_session.py tests/core/test_agent_session.py
git commit -m "feat: add auto-compaction and retry to AgentSession"
```

---

## Task 16: Configuration Loading

**Files:**
- Create: `mypi/config.py`

- [ ] **Step 1: Implement `mypi/config.py`** (no unit test needed — pure data class)

```python
from __future__ import annotations
import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_CONFIG_PATH = Path.home() / ".mypi" / "config.toml"

DEFAULT_CONFIG = """
[provider]
base_url = "https://api.openai.com/v1"
api_key  = ""
model    = "gpt-4o"

[session]
compaction_threshold = 0.80
max_retries = 3

[paths]
sessions_dir  = "~/.mypi/sessions"
skills_dir    = "~/.mypi/skills"
extensions_dir = "~/.mypi/extensions"
"""


@dataclass
class ProviderConfig:
    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    model: str = "gpt-4o"


@dataclass
class SessionConfig:
    compaction_threshold: float = 0.80
    max_retries: int = 3


@dataclass
class PathsConfig:
    sessions_dir: Path = field(default_factory=lambda: Path.home() / ".mypi" / "sessions")
    skills_dir: Path = field(default_factory=lambda: Path.home() / ".mypi" / "skills")
    extensions_dir: Path = field(default_factory=lambda: Path.home() / ".mypi" / "extensions")


@dataclass
class Config:
    provider: ProviderConfig = field(default_factory=ProviderConfig)
    session: SessionConfig = field(default_factory=SessionConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)


def load_config(config_path: Path | None = None) -> Config:
    path = config_path or DEFAULT_CONFIG_PATH
    raw: dict = {}
    if path.exists():
        with path.open("rb") as f:
            raw = tomllib.load(f)

    p = raw.get("provider", {})
    s = raw.get("session", {})
    paths = raw.get("paths", {})

    # Environment variables override config file
    api_key = os.environ.get("OPENAI_API_KEY") or p.get("api_key", "")
    base_url = os.environ.get("OPENAI_BASE_URL") or p.get("base_url", "https://api.openai.com/v1")

    return Config(
        provider=ProviderConfig(
            base_url=base_url,
            api_key=api_key,
            model=p.get("model", "gpt-4o"),
        ),
        session=SessionConfig(
            compaction_threshold=s.get("compaction_threshold", 0.80),
            max_retries=s.get("max_retries", 3),
        ),
        paths=PathsConfig(
            sessions_dir=Path(paths.get("sessions_dir", "~/.mypi/sessions")).expanduser(),
            skills_dir=Path(paths.get("skills_dir", "~/.mypi/skills")).expanduser(),
            extensions_dir=Path(paths.get("extensions_dir", "~/.mypi/extensions")).expanduser(),
        ),
    )
```

- [ ] **Step 2: Commit**

```bash
git add mypi/config.py
git commit -m "feat: add configuration loading with tomllib and env var overrides"
```

---

## Task 17: Print Mode

**Files:**
- Create: `mypi/modes/print_mode.py`
- Create: `tests/modes/test_print_mode.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/modes/test_print_mode.py
import pytest
import asyncio
from io import StringIO
from unittest.mock import MagicMock, AsyncMock, patch
from codepi.modes.print_mode import PrintMode
from codepi.ai.provider import TokenEvent, DoneEvent, TokenUsage
from codepi.core.session_manager import SessionManager


def make_mock_provider(events):
    async def stream(*args, **kwargs):
        for e in events:
            yield e
    p = MagicMock()
    p.stream = stream
    return p


@pytest.mark.asyncio
async def test_print_mode_outputs_tokens_to_stdout(tmp_sessions_dir):
    provider = make_mock_provider([
        TokenEvent(text="Hello"),
        TokenEvent(text=", world"),
        DoneEvent(usage=TokenUsage(10, 5)),
    ])
    sm = SessionManager(tmp_sessions_dir)
    sm.new_session(model="gpt-4o")

    output = StringIO()
    mode = PrintMode(provider=provider, session_manager=sm, model="gpt-4o", output=output)
    await mode.run("say hello")

    result = output.getvalue()
    assert "Hello" in result
    assert ", world" in result


@pytest.mark.asyncio
async def test_print_mode_shows_tool_calls(tmp_sessions_dir):
    from codepi.ai.provider import LLMToolCallEvent
    from codepi.tools.base import Tool, ToolResult, ToolRegistry

    class EchoTool(Tool):
        name = "echo"; description = "echo"
        input_schema = {"type": "object", "properties": {"text": {"type": "string"}}}
        async def execute(self, text=""): return ToolResult(output=text)

    registry = ToolRegistry()
    registry.register(EchoTool())

    provider = make_mock_provider([
        LLMToolCallEvent(id="c1", name="echo", arguments={"text": "hi"}),
        DoneEvent(usage=TokenUsage(10, 5)),
    ])
    sm = SessionManager(tmp_sessions_dir)
    sm.new_session(model="gpt-4o")

    output = StringIO()
    mode = PrintMode(provider=provider, session_manager=sm, model="gpt-4o",
                     tool_registry=registry, output=output)
    await mode.run("use echo")
    assert "echo" in output.getvalue()
```

- [ ] **Step 2: Run to verify it fails**

```bash
pytest tests/modes/test_print_mode.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `mypi/modes/print_mode.py`**

```python
from __future__ import annotations
import sys
from typing import IO
from codepi.core.agent_session import AgentSession
from codepi.core.session_manager import SessionManager
from codepi.ai.provider import LLMProvider
from codepi.tools.base import ToolRegistry


class PrintMode:
    def __init__(
        self,
        provider: LLMProvider,
        session_manager: SessionManager,
        model: str,
        tool_registry: ToolRegistry | None = None,
        extensions: list = None,
        system_prompt: str | None = None,
        output: IO[str] = sys.stdout,
    ):
        self.output = output
        kwargs = dict(
            provider=provider,
            session_manager=session_manager,
            model=model,
            tool_registry=tool_registry,
            extensions=extensions or [],
        )
        if system_prompt:
            kwargs["system_prompt"] = system_prompt
        self.session = AgentSession(**kwargs)
        self.session.on_token = lambda t: self._write(t)
        self.session.on_tool_call = lambda name, args: self._write(f"\n[tool: {name}] {args}\n")
        self.session.on_tool_result = lambda name, result: self._write(f"[result: {name}] {result.output[:200]}\n")
        self.session.on_error = lambda msg: self._write(f"\nError: {msg}\n")

    def _write(self, text: str) -> None:
        self.output.write(text)
        self.output.flush()

    async def run(self, prompt: str) -> None:
        await self.session.prompt(prompt)
        self._write("\n")
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/modes/test_print_mode.py -v
```

Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add mypi/modes/print_mode.py tests/modes/test_print_mode.py
git commit -m "feat: implement print mode for scripting and e2e testing"
```

---

## Task 18: RPC Mode

**Files:**
- Create: `mypi/modes/rpc.py`
- Create: `tests/modes/test_rpc.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/modes/test_rpc.py
import json
import pytest
import asyncio
from io import StringIO, BytesIO
from unittest.mock import MagicMock
from codepi.modes.rpc import RPCMode
from codepi.ai.provider import TokenEvent, DoneEvent, TokenUsage
from codepi.core.session_manager import SessionManager


def make_mock_provider(events):
    async def stream(*args, **kwargs):
        for e in events:
            yield e
    p = MagicMock()
    p.stream = stream
    return p


@pytest.mark.asyncio
async def test_rpc_mode_emits_token_jsonl(tmp_sessions_dir, capsys):
    provider = make_mock_provider([
        TokenEvent(text="Hello"),
        DoneEvent(usage=TokenUsage(10, 5)),
    ])
    sm = SessionManager(tmp_sessions_dir)
    sm.new_session(model="gpt-4o")

    stdin_data = json.dumps({"type": "prompt", "text": "hello"}) + "\n"
    stdin_data += json.dumps({"type": "exit"}) + "\n"
    stdin = asyncio.StreamReader()
    stdin.feed_data(stdin_data.encode())
    stdin.feed_eof()

    mode = RPCMode(provider=provider, session_manager=sm, model="gpt-4o")
    await mode.run(reader=stdin)

    captured = capsys.readouterr()
    lines = [l for l in captured.out.strip().split("\n") if l]
    types = [json.loads(l)["type"] for l in lines]
    assert "token" in types
    assert "done" in types
```

- [ ] **Step 2: Run to verify it fails**

```bash
pytest tests/modes/test_rpc.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `mypi/modes/rpc.py`**

```python
from __future__ import annotations
import asyncio
import json
import sys
from codepi.core.agent_session import AgentSession
from codepi.core.session_manager import SessionManager
from codepi.ai.provider import LLMProvider
from codepi.tools.base import ToolRegistry


class RPCMode:
    def __init__(
        self,
        provider: LLMProvider,
        session_manager: SessionManager,
        model: str,
        tool_registry: ToolRegistry | None = None,
        extensions: list = None,
    ):
        self._session = AgentSession(
            provider=provider,
            session_manager=session_manager,
            model=model,
            tool_registry=tool_registry,
            extensions=extensions or [],
        )
        self._write_line_fn = None

        self._session.on_token = lambda t: self._emit({"type": "token", "text": t})
        self._session.on_tool_call = lambda n, a: self._emit({"type": "tool_call", "name": n, "arguments": a})
        self._session.on_tool_result = lambda n, r: self._emit({"type": "tool_result", "name": n, "content": r.output})
        self._session.on_error = lambda m: self._emit({"type": "error", "message": m})

    def _emit(self, obj: dict) -> None:
        # Write synchronously — callbacks fire inside AgentSession's async loop,
        # so the event loop is running but we must not yield. Use sync stdout write.
        sys.stdout.write(json.dumps(obj) + "\n")
        sys.stdout.flush()

    def _write(self, line: str) -> None:
        sys.stdout.write(line + "\n")
        sys.stdout.flush()

    async def run(self, reader: asyncio.StreamReader | None = None) -> None:
        if reader is None:
            reader = asyncio.StreamReader()
            asyncio.get_event_loop().add_reader(sys.stdin.fileno(), lambda: reader.feed_data(sys.stdin.buffer.read1()))

        while True:
            try:
                line = await reader.readline()
            except Exception:
                break
            if not line:
                break
            text = line.decode().strip()
            if not text:
                continue
            try:
                cmd = json.loads(text)
            except json.JSONDecodeError:
                await write_line(json.dumps({"type": "error", "message": f"Invalid JSON: {text}"}))
                continue

            cmd_type = cmd.get("type")
            if cmd_type == "prompt":
                await self._session.prompt(cmd.get("text", ""))
                self._write(json.dumps({"type": "done", "usage": {}}))
            elif cmd_type == "steer":
                await self._session.steer(cmd.get("text", ""))
                self._write(json.dumps({"type": "done", "usage": {}}))
            elif cmd_type == "follow_up":
                await self._session.follow_up(cmd.get("text", ""))
                self._write(json.dumps({"type": "done", "usage": {}}))
            elif cmd_type == "cancel":
                self._write(json.dumps({"type": "cancelled"}))
            elif cmd_type == "exit":
                break
            else:
                self._write(json.dumps({"type": "error", "message": f"Unknown command: {cmd_type}"}))
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/modes/test_rpc.py -v
```

Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add mypi/modes/rpc.py tests/modes/test_rpc.py
git commit -m "feat: implement JSONL RPC mode"
```

---

## Task 19: SDK Mode

**Files:**
- Create: `mypi/modes/sdk.py`
- Create: `tests/modes/test_sdk.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/modes/test_sdk.py
import pytest
from unittest.mock import MagicMock
from codepi.modes.sdk import SDK
from codepi.ai.provider import TokenEvent, DoneEvent, TokenUsage
from codepi.core.session_manager import SessionManager


def make_mock_provider(events):
    async def stream(*args, **kwargs):
        for e in events:
            yield e
    p = MagicMock()
    p.stream = stream
    return p


@pytest.mark.asyncio
async def test_sdk_prompt_returns_full_response(tmp_sessions_dir):
    provider = make_mock_provider([
        TokenEvent(text="The answer"),
        TokenEvent(text=" is 42"),
        DoneEvent(usage=TokenUsage(10, 5)),
    ])
    sm = SessionManager(tmp_sessions_dir)
    sm.new_session(model="gpt-4o")
    sdk = SDK(provider=provider, session_manager=sm, model="gpt-4o")
    response = await sdk.prompt("what is the answer?")
    assert "The answer" in response
    assert "42" in response


@pytest.mark.asyncio
async def test_sdk_stream_yields_tokens(tmp_sessions_dir):
    provider = make_mock_provider([
        TokenEvent(text="chunk1"),
        TokenEvent(text="chunk2"),
        DoneEvent(usage=TokenUsage(5, 3)),
    ])
    sm = SessionManager(tmp_sessions_dir)
    sm.new_session(model="gpt-4o")
    sdk = SDK(provider=provider, session_manager=sm, model="gpt-4o")
    chunks = []
    async for chunk in sdk.stream("hello"):
        chunks.append(chunk)
    assert "chunk1" in chunks
    assert "chunk2" in chunks
```

- [ ] **Step 2: Run to verify it fails**

```bash
pytest tests/modes/test_sdk.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `mypi/modes/sdk.py`**

```python
from __future__ import annotations
import asyncio
from typing import AsyncIterator
from codepi.core.agent_session import AgentSession
from codepi.core.session_manager import SessionManager
from codepi.ai.provider import LLMProvider
from codepi.tools.base import ToolRegistry


class SDK:
    """Embeddable Python API for mypi. Use prompt() for full response or stream() for streaming."""

    def __init__(
        self,
        provider: LLMProvider,
        session_manager: SessionManager,
        model: str,
        tool_registry: ToolRegistry | None = None,
        extensions: list = None,
        system_prompt: str | None = None,
    ):
        kwargs = dict(
            provider=provider,
            session_manager=session_manager,
            model=model,
            tool_registry=tool_registry,
            extensions=extensions or [],
        )
        if system_prompt:
            kwargs["system_prompt"] = system_prompt
        self._session = AgentSession(**kwargs)

    async def prompt(self, text: str) -> str:
        """Send a prompt and return the full assistant response as a string."""
        parts: list[str] = []
        self._session.on_token = lambda t: parts.append(t)
        await self._session.prompt(text)
        return "".join(parts)

    async def stream(self, text: str) -> AsyncIterator[str]:
        """Send a prompt and yield streaming tokens."""
        queue: asyncio.Queue[str | None] = asyncio.Queue()
        self._session.on_token = lambda t: queue.put_nowait(t)

        async def _run():
            await self._session.prompt(text)
            queue.put_nowait(None)  # sentinel

        task = asyncio.create_task(_run())
        while True:
            token = await queue.get()
            if token is None:
                break
            yield token
        await task
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/modes/test_sdk.py -v
```

Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add mypi/modes/sdk.py tests/modes/test_sdk.py
git commit -m "feat: implement embeddable SDK mode"
```

---

## Task 20: TUI Renderer

**Files:**
- Create: `mypi/tui/renderer.py`

No automated tests (TUI rendering is visual). Manual verification instead.

- [ ] **Step 1: Implement `mypi/tui/renderer.py`**

```python
from __future__ import annotations
from rich.console import Console
from rich.markdown import Markdown
from rich.text import Text
from rich.panel import Panel
from rich.live import Live
from rich.spinner import Spinner


class StreamingRenderer:
    """Renders streaming LLM output to the terminal using rich."""

    def __init__(self, console: Console | None = None):
        self.console = console or Console()
        self._buffer = ""
        self._live: Live | None = None

    def start_turn(self) -> None:
        """Called at the start of an assistant turn."""
        self._buffer = ""

    def append_token(self, token: str) -> None:
        """Append a streaming token and re-render."""
        self._buffer += token
        # Render accumulated markdown so far
        self.console.print(token, end="", highlight=False)

    def end_turn(self) -> None:
        """Called at the end of an assistant turn. Re-render complete markdown."""
        pass  # streaming already printed tokens inline

    def render_tool_call(self, name: str, args: dict) -> None:
        self.console.print(f"\n[bold cyan]● {name}[/bold cyan] {args}")

    def render_tool_result(self, name: str, content: str) -> None:
        preview = content[:300] + ("..." if len(content) > 300 else "")
        self.console.print(f"  [dim]└─ {preview}[/dim]")

    def render_user_message(self, text: str) -> None:
        self.console.print(f"\n[bold green]You:[/bold green] {text}")

    def render_error(self, message: str) -> None:
        self.console.print(f"\n[bold red]Error:[/bold red] {message}")

    def render_info(self, message: str) -> None:
        self.console.print(f"[dim]{message}[/dim]")
```

- [ ] **Step 2: Commit**

```bash
git add mypi/tui/renderer.py
git commit -m "feat: implement rich streaming markdown renderer"
```

---

## Task 21: TUI Components + App

**Files:**
- Create: `mypi/tui/components.py`
- Create: `mypi/tui/app.py`

No automated tests. Manual verification.

- [ ] **Step 1: Implement `mypi/tui/components.py`**

```python
from __future__ import annotations
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys


def make_keybindings(
    on_submit,
    on_follow_up,
    on_cancel,
    on_clear,
    on_checkpoint,
) -> KeyBindings:
    kb = KeyBindings()

    @kb.add("enter")
    def submit(event):
        buf = event.app.current_buffer
        text = buf.text
        buf.reset()
        on_submit(text)

    @kb.add("escape", "enter")  # Alt+Enter
    def follow_up(event):
        buf = event.app.current_buffer
        text = buf.text
        buf.reset()
        on_follow_up(text)

    @kb.add("escape")
    def cancel(event):
        on_cancel()

    @kb.add("c-l")
    def clear(event):
        on_clear()
        event.app.renderer.clear()

    @kb.add("c-s")
    def checkpoint(event):
        on_checkpoint()

    return kb


def default_toolbar(model: str, session_id: str) -> HTML:
    return HTML(f"<b>{model}</b>  session: {session_id[:8]}  <i>Enter: send  Alt+Enter: queue  Ctrl+C: exit</i>")
```

- [ ] **Step 2: Implement `mypi/tui/app.py`**

```python
from __future__ import annotations
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.formatted_text import HTML
from codepi.tui.components import make_keybindings, default_toolbar
from codepi.tui.renderer import StreamingRenderer
from rich.console import Console


class TUIApp:
    def __init__(self, model: str, session_id: str):
        self.model = model
        self.session_id = session_id
        self.console = Console()
        self.renderer = StreamingRenderer(console=self.console)
        self._prompt_session = PromptSession(
            history=InMemoryHistory(),
            bottom_toolbar=lambda: default_toolbar(self.model, self.session_id),
        )

    async def get_input(self, prompt: str = "> ") -> str:
        return await self._prompt_session.prompt_async(prompt)
```

- [ ] **Step 3: Commit**

```bash
git add mypi/tui/components.py mypi/tui/app.py
git commit -m "feat: implement TUI components with prompt_toolkit key bindings"
```

---

## Task 22: Interactive Mode

**Files:**
- Create: `mypi/modes/interactive.py`

No automated tests. Manual verification after Task 23.

- [ ] **Step 1: Implement `mypi/modes/interactive.py`**

```python
from __future__ import annotations
import asyncio
import sys
from codepi.core.agent_session import AgentSession
from codepi.core.session_manager import SessionManager
from codepi.ai.provider import LLMProvider
from codepi.tools.base import ToolRegistry
from codepi.tui.app import TUIApp
from codepi.extensions.base import Extension


class InteractiveMode:
    def __init__(
        self,
        provider: LLMProvider,
        session_manager: SessionManager,
        model: str,
        session_id: str,
        tool_registry: ToolRegistry | None = None,
        extensions: list[Extension] | None = None,
        system_prompt: str | None = None,
    ):
        self._session_manager = session_manager
        self._app = TUIApp(model=model, session_id=session_id)
        self._follow_up_queue: list[str] = []
        self._is_running = True

        kwargs = dict(
            provider=provider,
            session_manager=session_manager,
            model=model,
            tool_registry=tool_registry,
            extensions=extensions or [],
        )
        if system_prompt:
            kwargs["system_prompt"] = system_prompt
        self._session = AgentSession(**kwargs)
        self._session.on_token = lambda t: self._app.renderer.append_token(t)
        self._session.on_tool_call = lambda n, a: self._app.renderer.render_tool_call(n, a)
        self._session.on_tool_result = lambda n, r: self._app.renderer.render_tool_result(n, r.output)
        self._session.on_error = lambda m: self._app.renderer.render_error(m)

    async def run(self) -> None:
        self._app.renderer.render_info(f"mypi — model: {self._app.model}  Ctrl+C to exit")
        while self._is_running:
            try:
                text = await self._app.get_input()
            except (EOFError, KeyboardInterrupt):
                break
            if not text.strip():
                continue
            self._app.renderer.render_user_message(text)
            self._session.on_token = lambda t: self._app.renderer.append_token(t)
            await self._session.prompt(text)
            self._app.renderer.end_turn()

            for queued in self._follow_up_queue:
                await self._session.follow_up(queued)
            self._follow_up_queue.clear()
```

- [ ] **Step 2: Commit**

```bash
git add mypi/modes/interactive.py
git commit -m "feat: implement interactive TUI mode"
```

---

## Task 23: CLI Entry Point

**Files:**
- Create: `mypi/__main__.py`

- [ ] **Step 1: Implement `mypi/__main__.py`**

```python
from __future__ import annotations
import argparse
import asyncio
import sys
from pathlib import Path
from codepi.config import load_config
from codepi.ai.openai_compat import OpenAICompatProvider
from codepi.core.session_manager import SessionManager
from codepi.tools.builtins import make_builtin_registry
from codepi.extensions.loader import ExtensionLoader
from codepi.extensions.skill_loader import SkillLoader
from codepi.core.events import BeforeAgentStartEvent


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="mypi", description="Minimalist terminal coding assistant")
    p.add_argument("--print", dest="print_prompt", metavar="PROMPT", help="Run in print mode with given prompt")
    p.add_argument("--rpc", action="store_true", help="Run in RPC mode (JSONL stdin/stdout)")
    p.add_argument("--session", metavar="ID", help="Resume an existing session")
    p.add_argument("--model", metavar="MODEL", help="Override LLM model")
    p.add_argument("--skills-dir", metavar="DIR", action="append", dest="skills_dirs", help="Additional skills directory")
    p.add_argument("--base-url", metavar="URL", help="Override OpenAI-compatible base URL")
    p.add_argument("--config", metavar="PATH", help="Path to config.toml")
    return p


async def _run(args: argparse.Namespace) -> None:
    config = load_config(Path(args.config) if args.config else None)

    # CLI overrides
    if args.model:
        config.provider.model = args.model
    if args.base_url:
        config.provider.base_url = args.base_url

    provider = OpenAICompatProvider(
        base_url=config.provider.base_url,
        api_key=config.provider.api_key,
        default_model=config.provider.model,
    )

    # Session
    sm = SessionManager(sessions_dir=config.paths.sessions_dir)
    if args.session:
        sm.load_session(args.session)
        leaves = sm.get_leaf_ids()
        if len(leaves) > 1:
            # Spec: always show branch selector UI for multi-leaf sessions
            all_entries = {e.id: e for e in sm.load_all_entries()}
            print(f"\nSession has {len(leaves)} branches. Select one to resume:\n")
            for i, leaf_id in enumerate(leaves):
                # Show depth (distance from root) and last message preview
                entry = all_entries.get(leaf_id)
                depth = 0
                cur = leaf_id
                while all_entries.get(cur) and all_entries[cur].parent_id:
                    cur = all_entries[cur].parent_id
                    depth += 1
                preview = ""
                if entry and entry.type == "message":
                    preview = str(entry.data.get("content", ""))[:60]
                print(f"  [{i + 1}] depth={depth}  {preview}")
            print()
            while True:
                choice = input(f"Enter branch number (1-{len(leaves)}): ").strip()
                if choice.isdigit() and 1 <= int(choice) <= len(leaves):
                    sm.set_active_leaf(leaves[int(choice) - 1])
                    break
                print("Invalid choice, try again.")
        elif len(leaves) == 1:
            sm.set_active_leaf(leaves[0])
    else:
        session_id = sm.new_session(model=config.provider.model)

    # Tools
    registry = make_builtin_registry()

    # Extensions
    ext_loader = ExtensionLoader(extensions_dir=config.paths.extensions_dir)
    extensions = ext_loader.load()

    # Skills — inject via a synthetic extension
    skills_dirs = [config.paths.skills_dir]
    if args.skills_dirs:
        skills_dirs += [Path(d) for d in args.skills_dirs]
    skill_loader = SkillLoader(skills_dirs=skills_dirs)

    class SkillExtension:
        name = "skill-loader"
        async def on_before_agent_start(self, event: BeforeAgentStartEvent):
            return skill_loader.inject_skills(event)
        async def on_before_provider_request(self, event): return None
        async def on_tool_call(self, event): return None
        async def on_tool_result(self, event): return None
        async def on_session_fork(self, event): pass
        async def on_session_tree(self, event): pass
        def get_tools(self): return []
        def get_shortcuts(self): return {}
        def get_ui_components(self): return None

    all_extensions = [SkillExtension()] + extensions

    # Wrap registry tools with extension runner
    from codepi.core.agent_session import AgentSession
    class SimpleRunner:
        def __init__(self, exts):
            self._exts = exts
        async def fire_tool_call(self, event):
            for ext in self._exts:
                r = await ext.on_tool_call(event)
                if r is not None: event = r
            return event
        async def fire_tool_result(self, event):
            for ext in self._exts:
                r = await ext.on_tool_result(event)
                if r is not None: event = r
            return event

    runner = SimpleRunner(all_extensions)
    for tool in list(registry.all_tools()):
        registry.wrap(tool, runner)

    model = config.provider.model
    session_id = sm._session_id or "unknown"

    if args.print_prompt:
        from codepi.modes.print_mode import PrintMode
        mode = PrintMode(provider=provider, session_manager=sm, model=model,
                         tool_registry=registry, extensions=all_extensions)
        await mode.run(args.print_prompt)

    elif args.rpc:
        from codepi.modes.rpc import RPCMode
        mode = RPCMode(provider=provider, session_manager=sm, model=model,
                       tool_registry=registry, extensions=all_extensions)
        await mode.run()

    else:
        from codepi.modes.interactive import InteractiveMode
        mode = InteractiveMode(
            provider=provider, session_manager=sm, model=model,
            session_id=session_id,
            tool_registry=registry, extensions=all_extensions,
        )
        await mode.run()


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        asyncio.run(_run(args))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run all tests to make sure nothing is broken**

```bash
pytest tests/ -v
```

Expected: All PASS.

- [ ] **Step 3: Smoke test**

```bash
# Should print help without errors
python -m mypi --help
```

Expected: prints usage.

- [ ] **Step 4: Commit**

```bash
git add mypi/__main__.py
git commit -m "feat: add CLI entry point wiring all modes together"
```

---

## Final Verification

- [ ] **Run the full test suite**

```bash
pytest tests/ -v --tb=short
```

Expected: All tests PASS.

- [ ] **Smoke test print mode** (requires API key)

```bash
OPENAI_API_KEY=your-key mypi --print "say hello in one word"
```

Expected: prints a single word response to stdout.

- [ ] **Verify package is importable**

```bash
python -c "import codepi; from codepi.modes.sdk import SDK; print('OK')"
```

Expected: `OK`

- [ ] **Final commit**

```bash
git add -A
git commit -m "feat: complete mypi implementation"
```
