# mypi Design Spec
**Date:** 2026-03-17
**Status:** Approved

---

## Overview

`mypi` is a minimalist terminal-based coding assistant in Python, modeled on the architectural philosophy of `pi-coding-agent`. It provides a minimal core runtime with maximal extensibility via a Python extension system and a Claude Code–compatible skill system. The LLM backend supports any OpenAI-compatible endpoint.

---

## Goals

- Minimal core: only what is essential for the agent runtime and built-in tools
- Maximal extensibility: Python extensions and Markdown skills cover everything else
- Streaming-first: all LLM output streams to the terminal in real time
- Session persistence: tree-structured JSONL branching and compaction
- Skill compatibility: skill files follow Claude Code format (YAML frontmatter + Markdown body)

---

## Non-Goals

- Built-in sub-agents or planning modes (these belong in extensions)
- Multi-provider abstraction beyond OpenAI-compatible API format
- Web or GUI interface
- `@file` reference syntax in user input (can be added as an extension)
- Automatic skill activation based on prompt content (skills are always injected)

---

## Package Structure

```
mypi/
├── ai/
│   ├── __init__.py
│   ├── provider.py          # Abstract LLMProvider base class
│   └── openai_compat.py     # OpenAI-compatible streaming implementation
│
├── core/
│   ├── __init__.py
│   ├── events.py            # Typed event dataclasses
│   ├── agent_session.py     # LLM loop, retry, compaction, event bus
│   └── session_manager.py   # JSONL tree persistence, branching, migration
│
├── tools/
│   ├── __init__.py
│   ├── base.py              # Tool ABC + ToolRegistry
│   └── builtins.py          # read, write, edit, bash, find, grep, ls
│
├── extensions/
│   ├── __init__.py
│   ├── base.py              # Extension ABC + hook types
│   ├── loader.py            # Python extension loader + watchdog hot-reload
│   └── skill_loader.py      # Markdown skill parser → system prompt injection
│
├── tui/
│   ├── __init__.py
│   ├── app.py               # prompt_toolkit Application setup
│   ├── renderer.py          # rich streaming markdown renderer
│   └── components.py        # Input area, status bar, tool call display
│
├── modes/
│   ├── __init__.py
│   ├── interactive.py       # Full TUI mode (default)
│   ├── print_mode.py        # Streaming stdout, no TUI
│   ├── rpc.py               # JSONL stdin/stdout protocol
│   └── sdk.py               # Embeddable Python API
│
└── __main__.py              # CLI entry point (argparse)
```

---

## Data Flow

```
User input
    │
    ▼
InteractiveMode (tui/)
    │  dispatches prompt
    ▼
AgentSession.prompt()  ──── event bus ────▶ Extensions
    │                                            │
    │  builds messages                    hook callbacks
    ▼
LLMProvider.stream()   ◀─── skills inject system prompt
    │
    │  streaming tokens + tool calls
    ▼
Tool registry dispatch  ──── ToolCallEvent ──▶ Extensions
    │
    │  results
    ▼
AgentSession  ─── stores in SessionManager (JSONL tree)
    │
    ▼
Renderer (rich) → terminal
```

---

## Layer 1: AI Provider (`mypi/ai/`)

### `provider.py`

Abstract base class:

```python
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

`ProviderEvent` union:
- `TokenEvent(text: str)` — streaming token
- `LLMToolCallEvent(id: str, name: str, arguments: dict)` — tool invocation from LLM stream
- `DoneEvent(usage: TokenUsage)` — stream complete

Note: `LLMToolCallEvent` is distinct from the extension-hook `ToolCallEvent` in `core/events.py`. The former is emitted by the provider layer when the LLM requests a tool; the latter is fired by `AgentSession` to allow extensions to intercept execution.

### `openai_compat.py`

Implements `LLMProvider` using the `openai` Python SDK with `stream=True`. Configurable via:
- `base_url` — any OpenAI-compatible endpoint
- `api_key`
- `default_model`

---

## Layer 2: Core Runtime (`mypi/core/`)

### `events.py`

Events fall into two categories based on mutability:

**Mutable events** — hooks may return a modified copy; `AgentSession` uses the returned value. Hook return type is `EventType | None` (returning `None` = no-op, keep original).
**Immutable (notification) events** — hooks return `None`; fired for observation only.

| Event | Category | Key fields | Purpose |
|-------|----------|-----------|---------|
| `BeforeAgentStartEvent` | Mutable | `system_prompt: str`, `messages: list[dict]` | Modify system prompt / messages before agent starts |
| `BeforeProviderRequestEvent` | Mutable | `params: dict` | Modify LLM request parameters |
| `ToolCallEvent` | Mutable | `tool_name: str`, `arguments: dict` | Intercept tool call before execution (distinct from `LLMToolCallEvent` in `ai/`) |
| `ToolResultEvent` | Mutable | `tool_name: str`, `result: ToolResult` | Intercept/replace tool result |
| `SessionForkEvent` | Notification | `from_entry_id: str`, `new_entry_id: str` | Fired when `branch()` is called |
| `SessionTreeEvent` | Notification | `leaf_id: str` | Fired when active branch/leaf changes |
| `TokenStreamEvent` | Notification | `text: str` | Streaming token chunk — internal rendering use only, not dispatched to extensions |
| `AutoCompactionStartEvent` | Notification | — | Compaction started |
| `AutoCompactionEndEvent` | Notification | `summary: str` | Compaction finished |
| `AutoRetryStartEvent` | Notification | `attempt: int` | Retry started |
| `AutoRetryEndEvent` | Notification | `attempt: int` | Retry finished |

### `agent_session.py`

Three public entry points:
- `prompt(text)` — initial user message; if a tool call is in-flight, cancels it, appends a synthetic `ToolResultEvent` with a cancellation error, then sends the new message.
- `steer(text)` — inject a correction mid-turn. Valid only while a tool call is in-flight. Replaces the pending tool result with the steered text as a synthetic tool result, allowing the LLM to continue with the injected content. If called outside a tool-execution context (tokens streaming but no tool call active), it degrades gracefully to a queued `follow_up` and is stored as a regular `message` entry with `role: "user"`. When used in the intended tool-in-flight context, steered messages are stored with `role: "steer"` to distinguish them in session history.
- `follow_up(text)` — queue message to send after agent finishes current turn; stored as a regular `message` entry.

Internal loop:
```
prompt()
  → fire BeforeAgentStartEvent  (extensions modify system prompt)
  → fire BeforeProviderRequestEvent  (extensions modify params)
  → LLMProvider.stream()
      → on token:     fire TokenStreamEvent
      → on tool_call: fire ToolCallEvent → dispatch tool → fire ToolResultEvent
      → on done:      check token usage
          → if > threshold (default 80%):
              run_auto_compaction()
                → LLM summarizes last N messages
                → store CompactionEntry in SessionManager
                → continue
          → else: store MessageEntry in SessionManager
  → on API error (5xx / rate-limit): exponential backoff, max 3 retries
```

### `session_manager.py`

JSONL tree file at `~/.mypi/sessions/<session-id>.jsonl`.

**Entry types:**

| Type | Fields |
|------|--------|
| `session_info` | `version`, `created_at`, `model` |
| `message` | `role`, `content`, `tool_calls?` |
| `compaction` | `summary` |
| `branch_summary` | `summary`, `branch_from` |
| `model_change` | `model` |
| `label` | `name` |
| `custom` | `extension`, `data` |

All entries share: `id` (UUID), `parentId` (UUID or null).

**Key operations:**
- `append(entry)` — write new leaf to the current active branch
- `branch(entry_id)` — create a new branch starting from `entry_id`; fires `SessionForkEvent`; returns the new branch's root entry id
- `set_active_leaf(entry_id)` — switch the active leaf to a different branch tip; fires `SessionTreeEvent`
- `build_context(leaf_id)` — walk the parent chain from `leaf_id` to the root, collecting messages in order. At a `CompactionEntry`, discard all messages with timestamps before the compaction entry on the current traversal path, and inject the compaction summary as a system message. Compaction boundaries are path-local: a `CompactionEntry` on a sibling branch does not affect the current path's context.
- `get_leaf_ids()` — return all current branch tips (leaf node ids with no children), for branch selection UI
- `list_sessions()` — scan `~/.mypi/sessions/`
- `migrate(path)` — automatic v1→v2→v3 migration on load

**Resuming sessions (`--session <id>`):** When a session is resumed:
- If the session has exactly one leaf (no branching), resume it directly.
- If the session has multiple leaves (branching has occurred), always show the branch selector UI — do not auto-select. The branch selector displays each leaf's depth and last message preview to help the user choose.

**Version history:**
- v1: flat entries, no tree
- v2: added `id`/`parentId`
- v3: renamed `hookMessage` → `custom`

---

## Layer 3: Tools (`mypi/tools/`)

### `base.py`

```python
class Tool(ABC):
    name: str
    description: str
    input_schema: dict  # JSON Schema

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult

class ExtensionRunner(Protocol):
    """Passed to ToolRegistry.wrap() so wrapped tools can fire extension hooks.
    Each fire_* method calls all registered extension hooks in order, threading
    the returned event through the chain. Returns the final (possibly modified) event."""
    async def fire_tool_call(self, event: ToolCallEvent) -> ToolCallEvent: ...
    async def fire_tool_result(self, event: ToolResultEvent) -> ToolResultEvent: ...

class ToolRegistry:
    def register(self, tool: Tool) -> None
    def wrap(self, tool: Tool, runner: ExtensionRunner) -> Tool  # before/after hooks
    def to_openai_schema(self) -> list[dict]  # for LLM request
```

### `builtins.py` — 7 tools

| Tool | Key behavior |
|------|-------------|
| `read` | Read file content; optional `offset` + `limit` line parameters |
| `write` | Write/overwrite file at path |
| `edit` | Replace `old_string` → `new_string`; fails if `old_string` not unique |
| `bash` | `asyncio.subprocess`; configurable timeout; fires action hooks |
| `find` | Glob pattern matching; results sorted by modification time |
| `grep` | Attempts `rg` (ripgrep) subprocess first; falls back to Python `re`-based search if `rg` is not on PATH |
| `ls` | Directory listing with file metadata (size, mtime, type) |

---

## Layer 4: Extension System (`mypi/extensions/`)

### `base.py`

```python
class Extension(ABC):
    name: str

    # Mutable hooks — return modified event or None (no-op)
    async def on_before_agent_start(self, event: BeforeAgentStartEvent) -> BeforeAgentStartEvent | None: ...
    async def on_before_provider_request(self, event: BeforeProviderRequestEvent) -> BeforeProviderRequestEvent | None: ...
    async def on_tool_call(self, event: ToolCallEvent) -> ToolCallEvent | None: ...
    async def on_tool_result(self, event: ToolResultEvent) -> ToolResultEvent | None: ...

    # Notification hooks — return None, observation only
    async def on_session_fork(self, event: SessionForkEvent) -> None: ...
    async def on_session_tree(self, event: SessionTreeEvent) -> None: ...

    # Registration
    def get_tools(self) -> list[Tool]: ...                      # register custom tools
    def get_shortcuts(self) -> dict[str, Callable]: ...         # keyboard bindings
    def get_ui_components(self) -> UIComponents | None: ...     # header / footer / widgets

@dataclass
class UIComponents:
    header: Callable[[], str] | None = None   # returns rich-renderable string
    footer: Callable[[], str] | None = None   # returns rich-renderable string
    widgets: dict[str, Callable[[], str]] = field(default_factory=dict)  # key → renderer
```

### `skill_loader.py`

- Scans `~/.mypi/skills/` and `<cwd>/.mypi/skills/` for `*.md` files
- Parses YAML frontmatter: `name`, `description`, `compatibility` (optional)
- Skill format is identical to Claude Code skill format
- All discovered skills are injected into the system prompt unconditionally via `BeforeAgentStartEvent`; the LLM reads the `description` field to determine relevance per request
- Operators are responsible for keeping the skills directories lean to avoid unnecessary token inflation
- `compatibility` field is parsed but not enforced at runtime (informational only)

### `loader.py`

- Scans `~/.mypi/extensions/` for `*.py` files
- Dynamically imports and instantiates all `Extension` subclasses found
- Uses `watchdog` to monitor for file changes
- Hot-reload is deferred until the agent is idle (not in a tool-call or streaming turn) to avoid race conditions with in-flight tool calls
- On reload: re-imports module, re-instantiates extension, re-registers tools/hooks; old extension instance is discarded

---

## Layer 5: TUI (`mypi/tui/`)

Built on `prompt_toolkit` (input) + `rich` (output rendering).

### Layout

```
┌─────────────────────────────────────────────────────┐
│  [header]  model: gpt-4o  tokens: 4,231/8k          │  ← extensions can replace
├─────────────────────────────────────────────────────┤
│                                                     │
│  You: help me refactor this function                │
│                                                     │
│  ● read  src/foo.py                                 │  ← tool call (collapsible)
│    └─ [12 lines returned]                           │
│                                                     │
│  Assistant: Here's the refactored version...        │  ← streaming rich markdown
│  ```python                                          │
│  def foo(): ...                                     │
│  ```                                                │
│                                                     │
├─────────────────────────────────────────────────────┤
│  > _                                                │  ← prompt_toolkit input
├─────────────────────────────────────────────────────┤
│  [footer]  session: abc123  cost: $0.012  ESC:cancel │  ← extensions can replace
└─────────────────────────────────────────────────────┘
```

### Key Bindings

| Key | Action |
|-----|--------|
| `Enter` | Send message (interrupts current tool execution) |
| `Alt+Enter` | Queue follow-up (waits for agent to finish) |
| `Escape` | Cancel, revert to editor |
| `Ctrl+C` | Exit |
| `Ctrl+L` | Clear display |
| `Ctrl+S` | Create session label/checkpoint |

---

## Layer 6: Modes (`mypi/modes/`)

| Mode | Entry | Description |
|------|-------|-------------|
| `interactive` | `mypi` | Full TUI — default |
| `print` | `mypi --print "prompt"` | Streaming stdout, no TUI |
| `rpc` | `mypi --rpc` | JSONL on stdin/stdout for tooling integration |
| `sdk` | `from mypi import SDK` | Embeddable Python API |

### RPC Protocol

One JSON object per line on stdin (commands) and stdout (events). All objects have a `type` field.

**Inbound commands (stdin → mypi):**
```jsonc
{"type": "prompt",    "text": "refactor foo.py"}
{"type": "steer",     "text": "use snake_case"}
{"type": "follow_up", "text": "also add docstrings"}
{"type": "cancel"}
{"type": "exit"}
```

**Outbound events (mypi → stdout):**
```jsonc
{"type": "token",       "text": "Here is the refactored..."}
{"type": "tool_call",   "id": "c1", "name": "read", "arguments": {"path": "foo.py"}}
{"type": "tool_result", "id": "c1", "content": "def foo(): ..."}
{"type": "done",        "usage": {"input_tokens": 1200, "output_tokens": 340}}
{"type": "error",       "message": "Rate limit exceeded", "retrying": true}
{"type": "compaction",  "summary": "Prior context summarized."}
```

Each line is a complete, valid JSON object terminated by `\n`. Callers must handle partial lines gracefully (buffer until `\n`).

---

## CLI (`mypi/__main__.py`)

```
mypi                           → interactive mode
mypi --print "refactor foo"    → print mode
mypi --rpc                     → rpc mode
mypi --session <id>            → resume existing session
mypi --model gpt-4o            → override model
mypi --skills-dir ./skills     → additional skills directory
mypi --base-url http://...     → custom OpenAI-compatible endpoint
```

---

## Configuration

`~/.mypi/config.toml`:
```toml
[provider]
base_url = "https://api.openai.com/v1"
api_key  = ""          # or set OPENAI_API_KEY env var
model    = "gpt-4o"

[session]
compaction_threshold = 0.80   # fraction of context window
max_retries          = 3

[paths]
sessions_dir  = "~/.mypi/sessions"
skills_dir    = "~/.mypi/skills"
extensions_dir = "~/.mypi/extensions"
```

---

## Dependencies

```toml
[dependencies]
openai         = ">=1.0"      # OpenAI-compatible client
rich           = ">=13.0"     # Markdown rendering, syntax highlighting
prompt_toolkit = ">=3.0"      # TUI input, key bindings
watchdog       = ">=4.0"      # Extension hot-reload
pyyaml         = ">=6.0"      # Skill frontmatter parsing
# Config parsed with stdlib tomllib (Python 3.11+) — no third-party toml package needed
```

Python 3.11+ (uses `tomllib` from stdlib, `asyncio.TaskGroup`).

---

## Error Handling

- **API errors (5xx, rate limits):** exponential backoff, max 3 retries, surface to user after exhaustion
- **Tool errors:** captured as `ToolResult(error=...)`, returned to LLM as error content
- **Compaction failures:** logged, session continues without compaction
- **Extension errors:** logged and isolated — a broken extension never crashes the core
- **Session file corruption:** migration attempted; if unrecoverable, session starts fresh with warning

---

## Testing Strategy

- Unit tests for `session_manager.py` (tree operations, context reconstruction, migration)
- Unit tests for all 7 built-in tools (mocked filesystem / subprocess)
- Integration tests for `agent_session.py` with a mock `LLMProvider`
- End-to-end test for `print` mode (easiest to assert on stdout)
- No TUI tests (prompt_toolkit apps are difficult to test headlessly)
