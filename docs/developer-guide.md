# mypi Developer Guide

## Table of Contents

1. [Architecture Overview](#architecture-overview)
   - [Layer diagram](#layer-diagram)
   - [Data flow](#data-flow)
2. [Module Reference](#module-reference)
   - [mypi/ai/](#mypiai)
   - [mypi/core/](#mypicore)
   - [mypi/tools/](#mypitools)
   - [mypi/extensions/](#mypiextensions)
   - [mypi/tui/](#mypitui)
   - [mypi/modes/](#mypimodes)
3. [Extension API](#extension-api)
   - [Writing a Python extension](#writing-a-python-extension)
   - [Hook methods reference](#hook-methods-reference)
   - [Registering custom tools](#registering-custom-tools)
   - [Keyboard shortcuts](#keyboard-shortcuts)
   - [UI components](#ui-components)
4. [Skill Format](#skill-format)
5. [RPC Protocol](#rpc-protocol)
   - [Commands](#commands)
   - [Events](#events)
6. [SDK Usage](#sdk-usage)
7. [Session Storage Format](#session-storage-format)
   - [JSONL tree structure](#jsonl-tree-structure)
   - [Entry types](#entry-types)
   - [Context reconstruction](#context-reconstruction)
   - [Version migration](#version-migration)
8. [Adding a New Built-in Tool](#adding-a-new-built-in-tool)
9. [Running Tests](#running-tests)

---

## Architecture Overview

### Layer diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         CLI / Entry Point                    │
│                      mypi/__main__.py                        │
└──────────────────────────┬──────────────────────────────────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
    ┌─────▼──────┐  ┌──────▼──────┐  ┌─────▼──────┐  ┌──────────────┐
    │ Interactive│  │   Print     │  │    RPC     │  │     SDK      │
    │   Mode     │  │   Mode      │  │   Mode     │  │  (Python API)│
    └─────┬──────┘  └──────┬──────┘  └─────┬──────┘  └──────┬───────┘
          └────────────────┼────────────────┘                │
                           │                                  │
              ┌────────────▼────────────────────────────────-┘
              │             mypi/core/agent_session.py        │
              │              AgentSession                     │
              │   prompt() / steer() / follow_up()           │
              │   retry loop, auto-compaction, event hooks   │
              └─────────────┬──────────────────┬─────────────┘
                            │                  │
            ┌───────────────▼───┐   ┌──────────▼────────────┐
            │  mypi/ai/         │   │  mypi/core/            │
            │  LLMProvider      │   │  SessionManager        │
            │  (stream)         │   │  (JSONL persistence)   │
            └───────────────────┘   └────────────────────────┘
                            │
            ┌───────────────▼───────────────────────────────┐
            │  mypi/tools/ToolRegistry                      │
            │  read  write  edit  bash  find  grep  ls      │
            └───────────────────────────────────────────────┘
                            │
            ┌───────────────▼───────────────────────────────┐
            │  mypi/extensions/                             │
            │  Extension hook points + SkillLoader          │
            └───────────────────────────────────────────────┘
```

### Data flow

A single conversation turn proceeds as follows:

1. **Mode layer** receives user input and calls `AgentSession.prompt(text)`.
2. **AgentSession** appends a `message` entry (role `user`) to `SessionManager`, fires `BeforeAgentStartEvent` through all extensions, then fires `BeforeProviderRequestEvent`.
3. **AgentSession** calls `LLMProvider.stream()` with the assembled messages and tool schemas.
4. The provider yields `TokenEvent`, `LLMToolCallEvent`, and `DoneEvent` objects.
5. For each `TokenEvent`, AgentSession calls the `on_token` callback (the mode layer renders it).
6. For each `LLMToolCallEvent`, AgentSession:
   a. Fires `ToolCallEvent` through extensions (extensions may modify arguments).
   b. Executes the tool via `ToolRegistry`.
   c. Fires `ToolResultEvent` through extensions (extensions may modify the result).
   d. Calls `on_tool_result` callback.
   e. Stores the tool call and result for inclusion in the assistant message.
7. **Multi-turn tool calling**: If any tool calls were made, AgentSession appends the assistant message with `tool_calls` and all tool result messages back to the message list, then makes another LLM request to continue generation. This repeats until no more tool calls are requested.
8. On final `DoneEvent`, AgentSession checks if token usage exceeds the compaction threshold and runs auto-compaction if needed.
9. AgentSession appends `assistant` and `tool` messages to `SessionManager`.
10. **Mode layer** signals completion to the user.

---

## Module Reference

### mypi/ai/

**`provider.py`** — Abstract base class and shared data types.

- `LLMProvider` — ABC with a single abstract method `stream()`. Implement this to add a new LLM backend.
- `TokenEvent(text: str)` — A streaming text chunk.
- `LLMToolCallEvent(id, name, arguments)` — The LLM requested a tool call. Note: this is the provider-level event, distinct from the extension-level `ToolCallEvent`.
- `DoneEvent(usage: TokenUsage)` — Stream finished. Carries input and output token counts.
- `TokenUsage(input_tokens, output_tokens)` — Token accounting.
- `ProviderEvent` — Union type alias for the three event types above.

**`openai_compat.py`** — Concrete provider for any OpenAI-compatible REST API.

- `OpenAICompatProvider(base_url, api_key, default_model)` — Wraps `openai.AsyncOpenAI`. Handles streaming tool call argument accumulation (arguments may arrive across multiple chunks).

### mypi/core/

**`events.py`** — All event dataclasses used by the extension hook system.

Mutable events (extensions return the modified event, or `None` to leave unchanged):
- `BeforeAgentStartEvent(system_prompt, messages)` — Fired once per turn before streaming begins. Use it to modify the system prompt or inject messages.
- `BeforeProviderRequestEvent(params)` — Fired once per turn with an empty `params` dict. Add arbitrary kwargs to pass to `provider.stream()`.
- `ToolCallEvent(tool_name, arguments)` — Fired before each tool execution. Modify `arguments` to alter what gets passed to the tool.
- `ToolResultEvent(tool_name, result: ToolResult)` — Fired after each tool execution. Modify `result` to alter what the LLM sees.

Notification events (extensions return `None`; these are observation-only):
- `SessionForkEvent(from_entry_id, new_entry_id)` — Fired when a branch is created.
- `SessionTreeEvent(leaf_id)` — Fired when the session tree changes.

Internal-only (not dispatched to extensions):
- `TokenStreamEvent(text)` — Used by the TUI renderer.
- `AutoCompactionStartEvent` / `AutoCompactionEndEvent(summary)` — Bookend automatic compaction.
- `AutoRetryStartEvent(attempt)` / `AutoRetryEndEvent(attempt)` — Bookend automatic retries.

**`session_manager.py`** — JSONL-backed session persistence.

- `SessionManager(sessions_dir)` — Main class. See [Session Storage Format](#session-storage-format) for full details.
- `SessionEntry(type, data, id, parent_id)` — One line of the JSONL file. Serialises to/from JSON.

**`agent_session.py`** — The runtime loop.

- `AgentSession(provider, session_manager, model, tool_registry, extensions, system_prompt, compaction_threshold, max_retries, context_window)` — Main class.
- `AgentSession.prompt(text)` — Run one full turn. Raises `RuntimeError` if called while another turn is in progress.
- `AgentSession.steer(text)` — Inject a mid-turn correction. Replaces an in-flight tool result if one is pending; otherwise delegates to `follow_up`.
- `AgentSession.follow_up(text)` — Queue a follow-up message (runs as a new prompt after the current turn).
- Callbacks: `on_token`, `on_tool_call`, `on_tool_result`, `on_error` — Set these on the instance before calling `prompt()`.

### mypi/tools/

**`base.py`** — Tool infrastructure.

- `ToolResult(output, error, metadata)` — Return type for all tools. `error` is `None` on success.
- `Tool` — ABC. Subclass and set `name`, `description`, `input_schema` as class attributes. Implement `execute(**kwargs) -> ToolResult`.
- `ToolRegistry` — Holds named `Tool` instances. Methods: `register(tool)`, `get(name)`, `all_tools()`, `to_openai_schema()`.
- `_WrappedTool` — Internal. Wraps a `Tool` with extension interception via `ExtensionRunner`. Created by `ToolRegistry.wrap()`.

**`builtins.py`** — The seven built-in tools: `ReadTool`, `WriteTool`, `EditTool`, `BashTool`, `FindTool`, `GrepTool`, `LsTool`.

- `make_builtin_registry()` — Convenience factory. Returns a `ToolRegistry` pre-populated with all seven tools.

### mypi/extensions/

**`base.py`** — Extension ABC and UI types.

- `Extension` — ABC. All hook methods have default no-op implementations. See [Extension API](#extension-api).
- `UIComponents(header, footer, widgets)` — Dataclass for extension-provided TUI components. All fields are callables returning strings.

**`loader.py`** — Dynamic extension loading.

- `ExtensionLoader(extensions_dir)` — Scans a directory for `.py` files, imports them, finds `Extension` subclasses, and instantiates them.
- `ExtensionLoader.load()` — (Re-)loads all extensions. Safe to call multiple times.
- `ExtensionLoader.start_watching(on_idle)` — Starts a watchdog observer for hot-reload. Hot-reload only fires when `on_idle()` returns `True` (i.e., not during a turn).
- `ExtensionLoader.stop_watching()` — Stops the watchdog observer.

**`skill_loader.py`** — Skill file loading and injection.

- `SkillLoader(skills_dirs)` — Scans multiple directories for `.md` skill files with YAML frontmatter.
- `SkillLoader.load_skills()` — Returns a list of parsed skill dicts.
- `SkillLoader.inject_skills(event: BeforeAgentStartEvent)` — Appends all loaded skills to the system prompt in a "# Available Skills" section. Returns the modified event.

### mypi/tui/

**`renderer.py`** — Terminal output.

- `StreamingRenderer(console)` — Wraps a `rich.Console`. Methods: `start_turn()`, `append_token(token)`, `end_turn()`, `render_tool_call(name, args)`, `render_tool_result(name, content)`, `render_user_message(text)`, `render_error(message)`, `render_info(message)`.

**`components.py`** — Input widgets.

- `make_keybindings(on_follow_up, on_cancel, on_clear, on_checkpoint)` — Returns a `prompt_toolkit.KeyBindings` object with all interactive shortcuts wired up.
- `default_toolbar(model, session_id)` — Returns an HTML toolbar for the prompt session bottom bar.

**`app.py`** — Combines renderer and input into a complete TUI.

- `TUIApp(model, session_id, ...)` — Holds a `StreamingRenderer` and a `prompt_toolkit.PromptSession`. Call `get_input(prompt)` to await user input.

### mypi/modes/

**`interactive.py`** — `InteractiveMode` — The default user-facing mode. Wires `TUIApp` and `AgentSession` together.

**`print_mode.py`** — `PrintMode` — Single-shot mode. Writes all output to an `IO[str]` (defaults to `sys.stdout`).

**`rpc.py`** — `RPCMode` — JSONL subprocess protocol. See [RPC Protocol](#rpc-protocol).

**`sdk.py`** — `SDK` — Embeddable Python API. See [SDK Usage](#sdk-usage).

---

## Extension API

### Writing a Python extension

Place a `.py` file in `~/.mypi/extensions/`. The file must define at least one non-abstract subclass of `Extension`. The loader instantiates every such class it finds.

A minimal extension:

```python
# ~/.mypi/extensions/my_extension.py
from mypi.extensions.base import Extension
from mypi.core.events import BeforeAgentStartEvent

class MyExtension(Extension):
    name = "my-extension"

    async def on_before_agent_start(self, event: BeforeAgentStartEvent):
        # Append extra instructions to the system prompt
        new_prompt = event.system_prompt + "\n\nAlways respond in bullet points."
        return BeforeAgentStartEvent(
            system_prompt=new_prompt,
            messages=event.messages,
        )
```

The `name` class attribute is used in log messages. It must be set.

### Hook methods reference

All hooks are `async def` methods. Mutable hooks return the modified event object, or `None` to leave the event unchanged. Notification hooks always return `None`.

---

**`on_before_agent_start(event: BeforeAgentStartEvent) -> BeforeAgentStartEvent | None`**

Fired once at the beginning of every turn, before the LLM request is built.

Use it to:
- Append context to the system prompt (e.g., git status, current file, workspace metadata).
- Prepend or append messages to the conversation history.

```python
async def on_before_agent_start(self, event: BeforeAgentStartEvent):
    import subprocess
    git_status = subprocess.check_output(["git", "status", "--short"]).decode()
    new_prompt = event.system_prompt + f"\n\nCurrent git status:\n{git_status}"
    return BeforeAgentStartEvent(system_prompt=new_prompt, messages=event.messages)
```

---

**`on_before_provider_request(event: BeforeProviderRequestEvent) -> BeforeProviderRequestEvent | None`**

Fired just before `provider.stream()` is called. `event.params` is a dict passed as `**kwargs` to the provider.

Use it to inject provider-specific parameters:

```python
async def on_before_provider_request(self, event: BeforeProviderRequestEvent):
    event.params["temperature"] = 0.2
    return event
```

---

**`on_tool_call(event: ToolCallEvent) -> ToolCallEvent | None`**

Fired before each tool is executed. `event.tool_name` and `event.arguments` are both mutable.

Use it to log calls, block certain operations, or rewrite arguments:

```python
async def on_tool_call(self, event: ToolCallEvent):
    if event.tool_name == "bash" and "rm -rf" in event.arguments.get("command", ""):
        # Replace with a safe no-op
        event.arguments["command"] = "echo 'blocked'"
    return event
```

---

**`on_tool_result(event: ToolResultEvent) -> ToolResultEvent | None`**

Fired after each tool executes. `event.result` is a `ToolResult` object.

Use it to transform or filter tool output before it reaches the LLM:

```python
from mypi.tools.base import ToolResult

async def on_tool_result(self, event: ToolResultEvent):
    if event.tool_name == "read" and len(event.result.output) > 5000:
        truncated = event.result.output[:5000] + "\n[...truncated by extension]"
        return ToolResultEvent(
            tool_name=event.tool_name,
            result=ToolResult(output=truncated),
        )
    return None
```

---

**`on_session_fork(event: SessionForkEvent) -> None`**

Fired when a session branch is created. `event.from_entry_id` and `event.new_entry_id` identify the branch point.

---

**`on_session_tree(event: SessionTreeEvent) -> None`**

Fired when the session tree changes. `event.leaf_id` is the new active leaf.

---

### Registering custom tools

Override `get_tools()` to return a list of `Tool` instances. These are registered in the tool registry before the session starts.

```python
from mypi.extensions.base import Extension
from mypi.tools.base import Tool, ToolResult

class MyTool(Tool):
    name = "fetch_url"
    description = "Fetch the contents of a URL."
    input_schema = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL to fetch"},
        },
        "required": ["url"],
    }

    async def execute(self, url: str) -> ToolResult:
        import urllib.request
        try:
            with urllib.request.urlopen(url, timeout=10) as r:
                return ToolResult(output=r.read().decode("utf-8", errors="replace")[:10000])
        except Exception as e:
            return ToolResult(error=str(e))


class MyExtension(Extension):
    name = "fetch-extension"

    def get_tools(self) -> list:
        return [MyTool()]
```

Note: `get_tools()` is called by the mode layer after loading extensions. The returned tools are registered into the shared `ToolRegistry` before the first turn.

### Keyboard shortcuts

Override `get_shortcuts()` to return a dict mapping shortcut keys to callables. Key strings follow `prompt_toolkit` notation.

```python
def get_shortcuts(self) -> dict:
    return {
        "c-g": lambda: print("Ctrl+G pressed"),
    }
```

Shortcuts are registered with the `TUIApp`'s key bindings only in interactive mode.

### UI components

Override `get_ui_components()` to return a `UIComponents` instance. All fields are optional callables that return strings rendered by `rich`.

```python
from mypi.extensions.base import Extension, UIComponents

class StatusExtension(Extension):
    name = "status-bar"

    def get_ui_components(self) -> UIComponents:
        return UIComponents(
            header=lambda: "[bold]Project: mypi[/bold]",
            footer=lambda: f"[dim]tokens used: {self._tokens}[/dim]",
            widgets={"status": lambda: "ready"},
        )
```

`header` and `footer` are rendered as `rich` markup strings. `widgets` is a dict of named content areas.

---

## Skill Format

Skills are `.md` files with YAML frontmatter. They are loaded from `~/.mypi/skills/` (and any additional `--skills-dir` directories) and injected into the system prompt at the start of every turn.

**File format:**

```markdown
---
name: <identifier>
description: <when-to-use description shown before the skill body>
compatibility: <optional metadata>
---

<Skill body — plain Markdown. Can contain headers, lists, code blocks.>
```

**Full example:**

```markdown
---
name: commit-message
description: Write a git commit message after making code changes
---

After making code changes, write a commit message following these rules:

1. First line: imperative mood, 50 characters max, no trailing period.
2. Blank line after first line if body follows.
3. Body: explain *why*, not *what* (the diff shows what).
4. Reference issue numbers as `Fixes #123`.

Run `git diff --staged` first to review what is staged.
Use `bash` to run `git commit -m "..."` to apply.
```

**How injection works:**

`SkillLoader.inject_skills()` appends the following block to the system prompt:

```
---
# Available Skills

## Skill: <name>
**When to use:** <description>

<body>

## Skill: <name2>
...
```

The LLM sees skills as standing instructions. Skills do not create commands or slash-commands; they are instructional text that the LLM can follow when it judges them relevant.

**Parser behaviour:**

- File must start with exactly `---` on the first line.
- The closing `---` must appear on its own line.
- Frontmatter is parsed with `yaml.safe_load`.
- Files missing `name` in frontmatter are silently skipped.
- Files that fail YAML parsing are silently skipped.

---

## RPC Protocol

mypi's RPC mode (`mypi --rpc`) implements a line-delimited JSON protocol on stdin/stdout. Each message is a single JSON object followed by `\n`. There is no framing header; each line is a self-contained message.

### Commands

Commands are sent to mypi's stdin.

**`prompt`** — Start a new turn with a user message.

```json
{"type": "prompt", "text": "What does src/main.py do?"}
```

**`steer`** — Inject a correction into the current or next turn.

```json
{"type": "steer", "text": "Focus only on the error handling"}
```

If a tool call is currently executing, its result is replaced by the steer text. Otherwise behaves like `follow_up`.

**`follow_up`** — Queue a follow-up message after the current turn completes.

```json
{"type": "follow_up", "text": "Now explain the tests"}
```

**`cancel`** — Cancel the current in-progress turn. Emits a `cancelled` event.

```json
{"type": "cancel"}
```

**`exit`** — Cleanly shut down the RPC process.

```json
{"type": "exit"}
```

### Events

Events are emitted to mypi's stdout.

**`token`** — A streaming text chunk from the LLM.

```json
{"type": "token", "text": "The main function"}
```

**`tool_call`** — The LLM requested a tool execution.

```json
{"type": "tool_call", "name": "read", "arguments": {"path": "src/main.py"}}
```

**`tool_result`** — A tool has finished executing.

```json
{"type": "tool_result", "name": "read", "content": "import asyncio\n..."}
```

**`error`** — An error occurred.

```json
{"type": "error", "message": "Failed after 3 attempts: Connection timeout"}
```

**`done`** — The current turn (prompt/steer/follow_up) has completed.

```json
{"type": "done", "usage": {}}
```

`usage` is currently an empty object. Token usage will be added in a future version.

**`cancelled`** — The current turn was cancelled.

```json
{"type": "cancelled"}
```

**Sequence diagram for a single prompt:**

```
Client                         mypi --rpc
  │                                │
  │── {"type":"prompt","text":"…"} ──►│
  │                                │
  │◄── {"type":"token","text":"…"} ──│  (zero or more)
  │◄── {"type":"tool_call", …}    ──│  (zero or more)
  │◄── {"type":"tool_result", …}  ──│  (zero or more)
  │◄── {"type":"done","usage":{}} ──│
  │                                │
```

---

## SDK Usage

The `SDK` class provides an async Python API for embedding mypi in another application. Import from `mypi.modes.sdk`.

### Setup

```python
from pathlib import Path
from mypi.config import load_config
from mypi.ai.openai_compat import OpenAICompatProvider
from mypi.core.session_manager import SessionManager
from mypi.tools.builtins import make_builtin_registry
from mypi.modes.sdk import SDK

config = load_config()

provider = OpenAICompatProvider(
    base_url=config.provider.base_url,
    api_key=config.provider.api_key,
    default_model=config.provider.model,
)

sm = SessionManager(sessions_dir=config.paths.sessions_dir)
sm.new_session(model=config.provider.model)

sdk = SDK(
    provider=provider,
    session_manager=sm,
    model=config.provider.model,
    tool_registry=make_builtin_registry(),
    system_prompt="You are a code review assistant.",  # optional
)
```

### `prompt(text) -> str`

Send a prompt and wait for the full response.

```python
import asyncio

async def main():
    response = await sdk.prompt("List all Python files in the project root.")
    print(response)

asyncio.run(main())
```

### `stream(text) -> AsyncIterator[str]`

Send a prompt and iterate over streaming tokens.

```python
async def main():
    async for token in sdk.stream("Explain the session manager module."):
        print(token, end="", flush=True)
    print()

asyncio.run(main())
```

### Multi-turn conversations

The `SessionManager` carries context between calls. Successive `prompt()` or `stream()` calls on the same `SDK` instance are part of the same conversation thread.

```python
async def main():
    r1 = await sdk.prompt("What tools are available?")
    r2 = await sdk.prompt("Which of those would you use to find a function definition?")
    # r2 has full context from r1
```

### Using extensions with the SDK

```python
from mypi.extensions.base import Extension
from mypi.core.events import BeforeAgentStartEvent

class LoggingExtension(Extension):
    name = "logger"
    async def on_before_agent_start(self, event: BeforeAgentStartEvent):
        print(f"[LOG] Turn started, {len(event.messages)} messages in context")
        return None

sdk = SDK(
    provider=provider,
    session_manager=sm,
    model=config.provider.model,
    extensions=[LoggingExtension()],
)
```

---

## Session Storage Format

### JSONL tree structure

Each session is a single `.jsonl` file at `~/.mypi/sessions/<uuid>.jsonl`. Each line is a JSON object (session entry).

Entries form a tree:
- Each entry has a unique `id` (UUID string).
- Each entry has a `parentId` (UUID string or `null` for the root entry).
- A leaf node is any entry that no other entry references as `parentId`.
- Branching is represented by two entries sharing the same `parentId`.

The file is append-only during a session. Entries are never deleted; compaction adds a new summary entry rather than removing old ones.

### Entry types

**`session_info`** — Always the first entry. Written once at session creation.

```json
{
  "id": "c2f9a3b1-...",
  "parentId": null,
  "type": "session_info",
  "version": 3,
  "model": "gpt-4o",
  "created_at": "2026-03-17T12:00:00+00:00"
}
```

**`message`** — A conversation message.

```json
{
  "id": "a1b2c3d4-...",
  "parentId": "c2f9a3b1-...",
  "type": "message",
  "role": "user",
  "content": "What does main.py do?"
}
```

```json
{
  "id": "e5f6a7b8-...",
  "parentId": "a1b2c3d4-...",
  "type": "message",
  "role": "assistant",
  "content": "The main.py file is the CLI entry point..."
}
```

```json
{
  "id": "f9e0d1c2-...",
  "parentId": "e5f6a7b8-...",
  "type": "message",
  "role": "tool",
  "tool_call_id": "call_abc123",
  "name": "read",
  "content": "import asyncio\n..."
}
```

**`compaction`** — A context summary written by auto-compaction.

```json
{
  "id": "d3c4b5a6-...",
  "parentId": "f9e0d1c2-...",
  "type": "compaction",
  "summary": "The user asked about the project structure. We examined main.py which is the CLI entry point..."
}
```

**`custom`** — Written by extensions for their own purposes. Structure is extension-defined.

```json
{
  "id": "b7a8c9d0-...",
  "parentId": "d3c4b5a6-...",
  "type": "custom",
  "extension": "my-extension",
  "data": {}
}
```

### Context reconstruction

`SessionManager.build_context(leaf_id)` reconstructs the message list for a given leaf:

1. Walk from `leaf_id` up to the root, following `parentId` links.
2. Reverse the path to get root-to-leaf order.
3. Iterate the path:
   - Skip `session_info` entries.
   - On a `compaction` entry: discard all previously accumulated messages, inject the summary as a `system` role message.
   - On a `message` entry: append to the message list.
4. Return the resulting message list.

This means compaction is path-local: each branch has its own compaction boundary.

### Version migration

`SessionManager` applies migrations at load time.

| Version | Change |
|---|---|
| v1 → v2 | Added `id` and `parentId` fields to all entries (linear chain). |
| v2 → v3 | Renamed `hookMessage` entry type to `custom`. |

Migrations rewrite the file in place. After migration the `session_info` entry's `version` field is updated.

---

## Adding a New Built-in Tool

1. **Add the tool class** to `mypi/tools/builtins.py`:

```python
class MyNewTool(Tool):
    name = "my_tool"
    description = "One-sentence description of what this tool does."
    input_schema = {
        "type": "object",
        "properties": {
            "param_one": {"type": "string", "description": "What this param is for"},
            "param_two": {"type": "integer", "description": "Optional param"},
        },
        "required": ["param_one"],
    }

    async def execute(self, param_one: str, param_two: int = 0) -> ToolResult:
        try:
            result = do_something(param_one, param_two)
            return ToolResult(output=str(result))
        except Exception as e:
            return ToolResult(error=str(e))
```

2. **Register it** in `make_builtin_registry()`:

```python
def make_builtin_registry() -> "ToolRegistry":
    from mypi.tools.base import ToolRegistry
    reg = ToolRegistry()
    for tool in [ReadTool(), WriteTool(), EditTool(), BashTool(),
                 FindTool(), GrepTool(), LsTool(), MyNewTool()]:  # add here
        reg.register(tool)
    return reg
```

3. **Write tests** in `tests/tools/test_builtins.py`. See the existing tests for patterns:
   - Use `pytest-asyncio` (`asyncio_mode = "auto"` is set in `pyproject.toml`).
   - Use `tmp_path` for file-system tests.
   - Test the success case and at least one error case.

4. **Document the tool** in `docs/user-guide.md` under the Built-in Tools section.

---

## Running Tests

Install dev dependencies first:

```bash
pip install -e ".[dev]"
```

Run all tests:

```bash
pytest
```

Run a specific test file:

```bash
pytest tests/core/test_agent_session.py
```

Run with verbose output:

```bash
pytest -v
```

Run tests matching a keyword:

```bash
pytest -k "compaction"
```

**Test layout:**

```
tests/
├── conftest.py               # Shared fixtures: tmp_sessions_dir, tmp_skills_dir, tmp_extensions_dir
├── ai/
│   └── test_provider.py      # LLMProvider and OpenAICompatProvider tests
├── core/
│   ├── test_events.py        # Event dataclass tests
│   ├── test_session_manager.py
│   └── test_agent_session.py
├── tools/
│   ├── test_base.py          # ToolRegistry and ToolResult tests
│   └── test_builtins.py      # Individual tool tests
├── extensions/
│   ├── test_base.py          # Extension ABC tests
│   ├── test_loader.py        # ExtensionLoader tests
│   └── test_skill_loader.py  # SkillLoader and frontmatter parsing tests
├── modes/
│   ├── test_print_mode.py
│   ├── test_rpc.py
│   └── test_sdk.py
└── integration/
    └── test_real_llm.py      # Integration tests against real LLM endpoints
```

All tests are async-compatible via `pytest-asyncio` with `asyncio_mode = "auto"`. You do not need to decorate individual test functions with `@pytest.mark.asyncio`.

**Integration tests:**

Integration tests in `tests/integration/` run against a real LLM endpoint. They are skipped automatically if `OPENAI_API_KEY` is not set.

```bash
# Run all tests (integration tests skipped if no API key)
pytest

# Run only integration tests
pytest tests/integration/

# Run with specific API endpoint
OPENAI_API_KEY="your-key" \
OPENAI_BASE_URL="http://localhost:8000/v1" \
OPENAI_MODEL="your-model" \
pytest tests/integration/test_real_llm.py -v
```
