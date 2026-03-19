# mypi Project Research Report

**Date:** 2026-03-18  
**Project:** mypi — Minimalist Terminal-Based Coding Assistant  
**Reference:** `pi-coding-agent` (TypeScript/Node.js monorepo)

---

## Executive Summary

**mypi** is a Python implementation of a minimalist terminal-based coding assistant inspired by the `pi-coding-agent` architecture. It connects to any OpenAI-compatible LLM API and gives the model file system and shell tools to read, edit, and execute code. The project emphasizes **minimal core** with **maximal extensibility** through Python extensions and Markdown skill files.

**Key Stats:**
- **Language:** Python 3.11+
- **Dependencies:** 5 runtime (openai, rich, prompt_toolkit, watchdog, pyyaml)
- **Source Files:** ~45 Python files
- **Architecture:** 6 layered modules (ai → core → tools → extensions → tui → modes)
- **Status:** Implementation complete with comprehensive test suite

---

## 1. Project Structure

```
mypi/
├── __main__.py                    # CLI entry point with argument parsing
├── config.py                      # TOML config loading with env var overrides
│
├── ai/                           # LLM Provider Abstraction Layer
│   ├── provider.py               # Abstract LLMProvider ABC + event types
│   └── openai_compat.py          # OpenAI-compatible streaming implementation
│
├── core/                         # Core Runtime
│   ├── events.py                 # Typed event dataclasses (10 events)
│   ├── agent_session.py          # LLM loop, retry, compaction (~200 lines)
│   └── session_manager.py        # JSONL tree persistence, branching, migration
│
├── tools/                        # Tool System
│   ├── base.py                   # Tool ABC, ToolResult, ToolRegistry
│   └── builtins.py               # 7 built-in tools (read, write, edit, bash, find, grep, ls)
│
├── extensions/                   # Extension System
│   ├── base.py                   # Extension ABC + UIComponents
│   ├── loader.py                 # Python extension loader + watchdog hot-reload
│   └── skill_loader.py           # Markdown skill parser → system prompt injection
│
├── tui/                          # Terminal UI
│   ├── app.py                   # TUIApp (prompt_toolkit integration)
│   ├── renderer.py               # StreamingRenderer (rich output)
│   └── components.py             # Keybindings + toolbar
│
└── modes/                        # Operation Modes
    ├── interactive.py            # Full TUI (default mode)
    ├── print_mode.py            # Streaming stdout
    ├── rpc.py                  # JSONL stdin/stdout protocol
    └── sdk.py                  # Embeddable Python API
```

---

## 2. Core Architecture

### 2.1 Layer Dependencies

The architecture follows a strict bottom-up layering:

```
┌─────────────────────────────────────────────────────────────┐
│  modes/ (interactive, print, rpc, sdk)                       │
│  → Depends on: tui/, core/, tools/, extensions/             │
└─────────────────────────────────────────────────────────────┘
                              ↑
┌─────────────────────────────────────────────────────────────┐
│  tui/ (app, renderer, components)                           │
│  → Depends on: core/, tools/                                 │
└─────────────────────────────────────────────────────────────┘
                              ↑
┌─────────────────────────────────────────────────────────────┐
│  extensions/ (base, loader, skill_loader)                    │
│  → Depends on: core/                                         │
└─────────────────────────────────────────────────────────────┘
                              ↑
┌─────────────────────────────────────────────────────────────┐
│  tools/ (base, builtins)                                    │
│  → Depends on: core/                                         │
└─────────────────────────────────────────────────────────────┘
                              ↑
┌─────────────────────────────────────────────────────────────┐
│  core/ (events, agent_session, session_manager)              │
│  → Depends on: ai/                                          │
└─────────────────────────────────────────────────────────────┘
                              ↑
┌─────────────────────────────────────────────────────────────┐
│  ai/ (provider, openai_compat)                              │
│  → No internal dependencies                                  │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Data Flow

```
User Input (via TUI or CLI)
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│  Mode Layer (interactive.py, print_mode.py, rpc.py, sdk.py) │
│  - Receives user input                                      │
│  - Sets up callbacks (on_token, on_tool_call, etc.)         │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│  AgentSession.prompt(text)                                  │
│  - Appends user message to SessionManager                    │
│  - Fires BeforeAgentStartEvent (extensions modify prompt)    │
│  - Fires BeforeProviderRequestEvent (extensions modify params)│
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│  LLMProvider.stream() → AsyncIterator[ProviderEvent]        │
│  - Wraps OpenAI-compatible REST API                          │
│  - Yields: TokenEvent, LLMToolCallEvent, DoneEvent           │
└─────────────────────────────────────────────────────────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌────────┐  ┌─────────────────────────────────────────────────┐
│ Token  │  │ LLMToolCallEvent                                │
│ Event  │  │ - Fire ToolCallEvent (extensions intercept)     │
│        │  │ - Execute tool via ToolRegistry                 │
│        │  │ - Fire ToolResultEvent (extensions modify)      │
└────────┘  └─────────────────────────────────────────────────┘
    │                        │
    ▼                        ▼
┌─────────────────────────────────────────────────────────────┐
│  Callbacks (render to terminal, store in session)            │
│  - on_token → StreamingRenderer                             │
│  - on_tool_call → render tool name + args                   │
│  - on_tool_result → render result preview                   │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│  SessionManager (JSONL append-only)                          │
│  - Store messages and tool calls                             │
│  - Auto-compaction when context exceeds threshold            │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Detailed Component Analysis

### 3.1 AI Provider Layer (`mypi/ai/`)

#### `provider.py` — Abstract Base Class

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

**Event Types:**
| Event | Fields | Purpose |
|-------|--------|---------|
| `TokenEvent` | `text: str` | Streaming text chunk |
| `LLMToolCallEvent` | `id: str`, `name: str`, `arguments: dict` | LLM requests tool call |
| `DoneEvent` | `usage: TokenUsage` | Stream complete with token counts |

#### `openai_compat.py` — Concrete Implementation

- Uses `openai.AsyncOpenAI` client
- Handles streaming tool call argument accumulation (multi-chunk JSON)
- Supports any OpenAI-compatible endpoint (Ollama, Groq, Azure, etc.)

**Key Implementation Detail:**
```python
# Tool calls arrive across multiple chunks
pending_tool_calls: dict[int, dict] = {}
for tc in delta.tool_calls:
    idx = tc.index
    if idx not in pending_tool_calls:
        pending_tool_calls[idx] = {"id": tc.id, "name": tc.function.name, "arguments": ""}
    if tc.function.arguments:
        pending_tool_calls[idx]["arguments"] += tc.function.arguments
```

---

### 3.2 Core Layer (`mypi/core/`)

#### `events.py` — Event System

**Mutable Events** (extensions return modified event or `None`):
| Event | Purpose |
|-------|---------|
| `BeforeAgentStartEvent` | Modify system prompt / messages |
| `BeforeProviderRequestEvent` | Modify LLM request parameters |
| `ToolCallEvent` | Intercept tool call before execution |
| `ToolResultEvent` | Intercept/modify tool result |

**Notification Events** (observation only, always return `None`):
| Event | Purpose |
|-------|---------|
| `SessionForkEvent` | Branch created |
| `SessionTreeEvent` | Active branch changed |
| `AutoCompactionStartEvent` | Compaction started |
| `AutoCompactionEndEvent` | Compaction finished |
| `AutoRetryStartEvent` | Retry started |
| `AutoRetryEndEvent` | Retry finished |

#### `agent_session.py` — Runtime Loop

**Three Entry Points:**

1. **`prompt(text)`** — Initial message
   - Appends message to session
   - Runs full turn
   - Raises `RuntimeError` if called while turn in progress

2. **`steer(text)`** — Mid-turn correction
   - Replaces in-flight tool result if tool call active
   - Falls back to `follow_up` if no tool call

3. **`follow_up(text)`** — Queued message
   - Runs as new prompt after current turn

**Retry Mechanism:**
```python
for attempt in range(self.max_retries):
    try:
        await self._stream_turn(evt, params_evt)
        return
    except Exception as e:
        if attempt == self.max_retries - 1:
            raise
        delay = 2 ** attempt  # Exponential backoff
        await asyncio.sleep(delay)
```

**Auto-Compaction:**
```python
if self._last_input_tokens > self._context_window * self.compaction_threshold:
    await self._run_auto_compaction()
```
- Triggers when input tokens exceed 80% of context window (configurable)
- LLM summarizes conversation
- Stores `CompactionEntry` in SessionManager

#### `session_manager.py` — Persistence

**JSONL Tree Structure:**
```
~/.mypi/sessions/<session-id>.jsonl
```

Each line is a JSON entry:
```json
{"id": "uuid1", "parentId": null, "type": "session_info", "version": 3, "model": "gpt-4o", "created_at": "..."}
{"id": "uuid2", "parentId": "uuid1", "type": "message", "role": "user", "content": "hello"}
{"id": "uuid3", "parentId": "uuid2", "type": "message", "role": "assistant", "content": "hi"}
```

**Entry Types:**
| Type | Fields | Purpose |
|------|--------|---------|
| `session_info` | `version`, `model`, `created_at` | Session metadata |
| `message` | `role`, `content`, `tool_call_id?`, `name?` | Conversation messages |
| `compaction` | `summary` | Context summary |
| `custom` | `extension`, `data` | Extension-specific data |

**Context Reconstruction Algorithm:**
```python
def build_context(self, leaf_id: str | None = None) -> list[dict]:
    # 1. Walk parent chain root→leaf
    # 2. Reverse to get root-to-leaf order
    # 3. For each entry:
    #    - session_info: skip
    #    - compaction: reset messages, inject summary as system message
    #    - message: append to list
    # 4. Return message list
```

**Version Migrations:**
- v1 → v2: Added `id`/`parentId` fields
- v2 → v3: Renamed `hookMessage` → `custom`

---

### 3.3 Tools Layer (`mypi/tools/`)

#### `base.py` — Tool Infrastructure

```python
class Tool(ABC):
    name: str
    description: str
    input_schema: dict  # JSON Schema
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult: ...

class ToolRegistry:
    def register(self, tool: Tool) -> None
    def wrap(self, tool: Tool, runner: ExtensionRunner) -> Tool
    def get(self, name: str) -> Tool | None
    def to_openai_schema(self) -> list[dict]
```

#### `builtins.py` — 7 Built-in Tools

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `read` | Read file contents | `path`, `offset` (1-based), `limit` |
| `write` | Write/overwrite file | `path`, `content` |
| `edit` | Replace unique string | `path`, `old_string`, `new_string` |
| `bash` | Execute shell command | `command`, `timeout` |
| `find` | Glob file search | `path`, `pattern` |
| `grep` | Regex content search | `pattern`, `path`, `glob` |
| `ls` | Directory listing | `path` |

**GrepTool Implementation Detail:**
```python
async def execute(self, pattern: str, path: str, glob: str | None = None):
    if shutil.which("rg"):  # Prefer ripgrep
        return await self._rg(pattern, path, glob)
    return await self._python_grep(pattern, path, glob)  # Fallback
```

---

### 3.4 Extensions Layer (`mypi/extensions/`)

#### `base.py` — Extension ABC

```python
class Extension(ABC):
    name: str
    
    # Mutable hooks
    async def on_before_agent_start(self, event) -> Event | None
    async def on_before_provider_request(self, event) -> Event | None
    async def on_tool_call(self, event) -> Event | None
    async def on_tool_result(self, event) -> Event | None
    
    # Notification hooks
    async def on_session_fork(self, event) -> None
    async def on_session_tree(self, event) -> None
    
    # Registration
    def get_tools(self) -> list[Tool]
    def get_shortcuts(self) -> dict[str, Callable]
    def get_ui_components(self) -> UIComponents | None
```

#### `loader.py` — Dynamic Extension Loading

- Scans `~/.mypi/extensions/*.py`
- Uses `importlib.util` for dynamic import
- `watchdog` for file system monitoring
- Hot-reload deferred until agent idle

#### `skill_loader.py` — Claude Code Skill Format

**File Format:**
```markdown
---
name: commit-message
description: Write a git commit message after making code changes
---

When writing commits:
1. Use imperative mood
2. First line ≤ 50 chars
...
```

**Injection:**
```python
def inject_skills(self, event: BeforeAgentStartEvent) -> BeforeAgentStartEvent:
    new_prompt = event.system_prompt + "\n\n---\n# Available Skills\n\n" + skills_text
    return BeforeAgentStartEvent(system_prompt=new_prompt, messages=event.messages)
```

---

### 3.5 TUI Layer (`mypi/tui/`)

**Stack:** `prompt_toolkit` (input) + `rich` (output)

#### `app.py` — Application Setup
```python
class TUIApp:
    def __init__(self, model, session_id, callbacks...):
        self._prompt_session = PromptSession(
            history=InMemoryHistory(),
            bottom_toolbar=lambda: default_toolbar(model, session_id),
            key_bindings=kb,
        )
```

#### `renderer.py` — Streaming Output
```python
class StreamingRenderer:
    def append_token(self, token: str) -> None:
        self._buffer += token
        self.console.print(token, end="", highlight=False)
```

#### `components.py` — Key Bindings

| Key | Action |
|-----|--------|
| `Enter` | Send message |
| `Alt+Enter` | Queue follow-up |
| `Escape` | Cancel |
| `Ctrl+L` | Clear display |
| `Ctrl+S` | Checkpoint |
| `Ctrl+C` | Exit |

---

### 3.6 Modes Layer (`mypi/modes/`)

| Mode | Entry Point | Purpose |
|------|-------------|---------|
| `interactive` | `mypi` | Full TUI experience |
| `print` | `mypi --print "prompt"` | Streaming stdout, scriptable |
| `rpc` | `mypi --rpc` | JSONL subprocess protocol |
| `sdk` | `from mypi.modes.sdk import SDK` | Embeddable Python API |

#### Print Mode
```python
class PrintMode:
    async def run(self, prompt: str) -> None:
        await self.session.prompt(prompt)
```

#### RPC Mode Protocol

**Inbound (stdin):**
```json
{"type": "prompt", "text": "..."}
{"type": "steer", "text": "..."}
{"type": "follow_up", "text": "..."}
{"type": "cancel"}
{"type": "exit"}
```

**Outbound (stdout):**
```json
{"type": "token", "text": "..."}
{"type": "tool_call", "name": "read", "arguments": {...}}
{"type": "tool_result", "name": "read", "content": "..."}
{"type": "error", "message": "..."}
{"type": "done", "usage": {}}
{"type": "cancelled"}
```

#### SDK
```python
sdk = SDK(provider=provider, session_manager=sm, model=model)
response = await sdk.prompt("What files are here?")
async for token in sdk.stream("Explain this"):
    print(token, end="", flush=True)
```

---

## 4. Configuration System

### 4.1 Config File (`~/.mypi/config.toml`)

```toml
[provider]
base_url = "https://api.openai.com/v1"
api_key  = ""
model    = "gpt-4o"

[session]
compaction_threshold = 0.80
max_retries = 3

[paths]
sessions_dir   = "~/.mypi/sessions"
skills_dir     = "~/.mypi/skills"
extensions_dir = "~/.mypi/extensions"
```

### 4.2 Environment Variables

| Variable | Overrides |
|----------|-----------|
| `OPENAI_API_KEY` | `provider.api_key` |
| `OPENAI_BASE_URL` | `provider.base_url` |

---

## 5. CLI Interface (`mypi/__main__.py`)

```bash
mypi                           # Interactive mode
mypi --print "prompt"         # Print mode
mypi --rpc                    # RPC mode
mypi --session <ID>           # Resume session
mypi --model gpt-4o           # Override model
mypi --skills-dir ./skills     # Additional skills directory
mypi --base-url http://...     # Custom API endpoint
mypi --config ./config.toml    # Custom config file
```

---

## 6. Testing Coverage

**Test Layout:**
```
tests/
├── conftest.py              # Shared fixtures
├── ai/
│   └── test_provider.py     # LLMProvider + OpenAICompatProvider
├── core/
│   ├── test_events.py       # Event dataclasses
│   ├── test_session_manager.py
│   └── test_agent_session.py
├── tools/
│   ├── test_base.py         # ToolRegistry + ToolResult
│   └── test_builtins.py     # All 7 built-in tools
├── extensions/
│   ├── test_base.py         # Extension ABC
│   ├── test_loader.py       # ExtensionLoader
│   └── test_skill_loader.py # Skill parsing
└── modes/
    ├── test_print_mode.py
    ├── test_rpc.py
    └── test_sdk.py
```

**Run Tests:**
```bash
pip install -e ".[dev]"
pytest           # All tests
pytest -v        # Verbose
pytest -k "tool" # Filtered
```

---

## 7. Reference: pi-coding-agent Architecture

The TypeScript reference (`pi-coding-agent`) provides the architectural template:

### Similarities
- **AgentSession** → `agent_session.py` (core runtime)
- **SessionManager** → `session_manager.py` (JSONL persistence)
- **Tool System** → `tools/` (7 built-in tools)
- **Extension System** → `extensions/` (hook-based)
- **4 Modes** → `modes/` (interactive, print, rpc, sdk)
- **TUI** → `tui/` (prompt_toolkit + rich)

### Differences from TypeScript Original
| Aspect | TypeScript (pi) | Python (mypi) |
|--------|-----------------|---------------|
| Package format | ESM modules | Single `mypi` package |
| Tool wrapping | Extension hooks | Protocol-based |
| Session storage | JSONL (same) | JSONL (same) |
| Config format | TypeScript config | TOML file |
| TUI framework | Custom (pi-tui) | prompt_toolkit + rich |

---

## 8. Key Design Decisions

### 8.1 Minimal Core Philosophy
- Only essential: 7 tools, basic session management, simple extension hooks
- No built-in sub-agents or planning modes
- Features added via extensions/skills

### 8.2 Async-First Design
- `AgentSession` and all tools are `async`
- `LLMProvider.stream()` returns `AsyncIterator`
- Enables concurrent tool execution (future enhancement)

### 8.3 Event-Driven Extensions
- All state changes broadcast via event bus
- Extensions subscribe to events they care about
- Mutable events allow extension interception

### 8.4 JSONL Persistence
- Append-only for crash safety
- Tree structure enables branching
- Version migrations for forward compatibility

### 8.5 Claude Code Skill Compatibility
- YAML frontmatter format matches Claude Code
- Skills injected unconditionally into system prompt
- LLM decides when to apply based on description

---

## 9. Dependencies Analysis

| Package | Version | Purpose |
|---------|---------|---------|
| `openai` | >=1.0 | OpenAI-compatible REST API client |
| `rich` | >=13.0 | Terminal rendering, markdown output |
| `prompt_toolkit` | >=3.0 | TTY input, key bindings, history |
| `watchdog` | >=4.0 | Extension hot-reload |
| `pyyaml` | >=6.0 | Skill file frontmatter parsing |

**Python stdlib used:**
- `tomllib` (3.11+) — Config parsing
- `asyncio` — Async runtime
- `pathlib` — Path operations
- `importlib.util` — Dynamic module loading

---

## 10. Future Extension Points

Based on the architecture, these features could be added as extensions:

1. **Git Integration** — Commit hooks, branch management
2. **Code Review** — PR analysis, lint integration
3. **Interactive Shell** — Persistent shell session
4. **DOOM Overlay** — Game Easter egg
5. **Planning Mode** — Structured task breakdown
6. **Web Search** — Research tool integration
7. **Database Tools** — Query execution

---

## 11. Summary

**mypi** is a well-architected, minimal coding assistant that successfully ports the `pi-coding-agent` philosophy to Python. Key strengths:

- ✅ Clean layered architecture
- ✅ Comprehensive event system
- ✅ JSONL tree persistence with migration
- ✅ Hot-reloadable extensions
- ✅ Claude Code skill compatibility
- ✅ 4 operation modes for flexibility
- ✅ Full test coverage

The project demonstrates solid software engineering with proper separation of concerns, async-first design, and extensibility as a first-class feature.
