# codepi Developer Guide

## Table of Contents

1. [Architecture Overview](#architecture-overview)
   - [Layer diagram](#layer-diagram)
   - [Data flow](#data-flow)
2. [Module Reference](#module-reference)
   - [codepi/ai/](#codepiai)
   - [codepi/core/](#codepicore)
   - [codepi/tools/](#codepitools)
   - [codepi/extensions/](#codepiextensions)
   - [codepi/templates/](#codepitemplates)
   - [codepi/tui/](#codepitui)
   - [codepi/modes/](#codepimodes)
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
│                      codepi/__main__.py                      │
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
              │           codepi/core/agent_session.py        │
              │                AgentSession                   │
              │   prompt() / steer() / follow_up()           │
              │   retry loop, auto-compaction, event hooks   │
              └─────────────┬──────────────────┬─────────────┘
                            │                  │
              ┌─────────────▼───┐   ┌──────────▼────────────┐
              │  codepi/ai/     │   │  codepi/core/          │
              │  LLMProvider    │   │  SessionManager        │
              │  (stream)       │   │  (JSONL persistence)   │
              └─────────────────┘   └────────────────────────┘
                            │
              ┌─────────────▼───────────────────────────────┐
              │  codepi/tools/ToolRegistry                   │
              │  read  write  edit  bash  find  grep  ls    │
              └──────────────────────────────────────────────┘
                            │
              ┌─────────────▼───────────────────────────────┐
              │  codepi/extensions/                          │
              │  Extension hook points + SkillLoader         │
              └──────────────────────────────────────────────┘
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
             │  read  write  edit  bash  find  grep  ls  skill │
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

### codepi/ai/

**`provider.py`** — Abstract base class and shared data types.

- `LLMProvider` — ABC with a single abstract method `stream()`. Implement this to add a new LLM backend.
- `TokenEvent(text: str)` — A streaming text chunk.
- `LLMToolCallEvent(id, name, arguments)` — The LLM requested a tool call. Note: this is the provider-level event, distinct from the extension-level `ToolCallEvent`.
- `DoneEvent(usage: TokenUsage)` — Stream finished. Carries input and output token counts.
- `TokenUsage(input_tokens, output_tokens)` — Token accounting.
- `ProviderEvent` — Union type alias for the three event types above.

**`openai_compat.py`** — Concrete provider for any OpenAI-compatible REST API.

- `OpenAICompatProvider(base_url, api_key, default_model)` — Wraps `openai.AsyncOpenAI`. Handles streaming tool call argument accumulation (arguments may arrive across multiple chunks).
- Uses `getattr(chunk, "usage", None)` for Ollama compatibility (Ollama doesn't include usage in all streaming chunks).

### codepi/core/

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

- `AgentSession(provider, session_manager, model, tool_registry, extensions, system_prompt, compaction_threshold, max_retries, context_window, skill_loader)` — Main class. `skill_loader` enables `/opsx:` command routing.
- `AgentSession.prompt(text)` — Run one full turn. Detects `/opsx:` prefix and routes to workflow skills. Raises `RuntimeError` if called while another turn is in progress.
- `AgentSession.steer(text)` — Inject a mid-turn correction. Replaces an in-flight tool result if one is pending; otherwise delegates to `follow_up`.
- `AgentSession.follow_up(text)` — Queue a follow-up message (runs as a new prompt after the current turn).
- `AgentSession._is_opsx_command(text)` — Returns `True` if text starts with `/opsx:`.
- `AgentSession._handle_opsx_command(text)` — Loads the matching workflow skill and injects its body as the user message.
- Callbacks: `on_token`, `on_tool_call`, `on_tool_result`, `on_error` — Set these on the instance before calling `prompt()`.

### codepi/tools/

**`base.py`** — Tool infrastructure.

- `ToolResult(output, error, metadata)` — Return type for all tools. `error` is `None` on success.
- `Tool` — ABC. Subclass and set `name`, `description`, `input_schema` as class attributes. Implement `execute(**kwargs) -> ToolResult`.
- `ToolRegistry` — Holds named `Tool` instances. Methods: `register(tool)`, `get(name)`, `all_tools()`, `to_openai_schema()`.
- `_WrappedTool` — Internal. Wraps a `Tool` with extension interception via `ExtensionRunner`. Created by `ToolRegistry.wrap()`.

**`builtins.py`** — The seven built-in tools: `ReadTool`, `WriteTool`, `EditTool`, `BashTool`, `FindTool`, `GrepTool`, `LsTool`, and `SkillTool`.

- `make_builtin_registry(skill_loader_getter=None)` — Convenience factory. Returns a `ToolRegistry` pre-populated with all eight tools. Pass a callable returning a `SkillLoader` instance to enable the `skill` tool.

**`skill_tool.py`** — On-demand skill content loading.

- `SkillTool(skill_loader_getter)` — Tool that loads full skill content by name. Accepts a getter function returning the `SkillLoader` instance.

**`lsp/`** — LSP-powered tools for Python code intelligence.

- `client.py` — `LSPClientManager` singleton that manages Python LSP server lifecycle (pyright, pylsp, or jedi-language-server).
- `goto_definition.py` — `lsp_goto_definition` tool.
- `find_references.py` — `lsp_find_references` tool.
- `diagnostics.py` — `lsp_diagnostics` tool.
- `hover.py` — `lsp_hover` tool.
- `rename.py` — `lsp_rename` tool.

### codepi/extensions/

**`base.py`** — Extension ABC and UI types.

- `Extension` — ABC. All hook methods have default no-op implementations. See [Extension API](#extension-api).
- `UIComponents(header, footer, widgets)` — Dataclass for extension-provided TUI components. All fields are callables returning strings.

**`loader.py`** — Dynamic extension loading.

- `ExtensionLoader(extensions_dir)` — Scans a directory for `.py` files, imports them, finds `Extension` subclasses, and instantiates them.
- `ExtensionLoader.load()` — (Re-)loads all extensions. Safe to call multiple times.
- `ExtensionLoader.start_watching(on_idle)` — Starts a watchdog observer for hot-reload. Hot-reload only fires when `on_idle()` returns `True` (i.e., not during a turn).
- `ExtensionLoader.stop_watching()` — Stops the watchdog observer.

**`skill_loader.py`** — Skill file loading and injection.

- `Skill(skills_dirs)` — Dataclass representing a skill with `name`, `description`, `file_path`, `compatibility`, optional `body`, and `metadata` (raw YAML frontmatter dict).
- `SkillLoader(skills_dirs)` — Scans multiple directories for `.md` skill files with YAML frontmatter. Package-managed skills are prepended so they take priority.
- `SkillLoader.set_package_skills_dir(path)` — Class method to set the package-managed skills directory. Call at startup before instantiating.
- `SkillLoader.load_skills_metadata()` — Returns a list of `Skill` objects with metadata only (name, description). Used for system prompt injection.
- `SkillLoader.load_skill_content(name)` — Returns a `Skill` with full body content for a specific skill. Used for on-demand loading.
- `SkillLoader.inject_skills(event: BeforeAgentStartEvent)` — Appends skill metadata to the system prompt in a "# Available Skills" section.

**`openspec/`** — Built-in OpenSpec core profile workflow skills.

- `skills/opsx-propose.md` — Propose skill: create a change with all planning artifacts.
- `skills/opsx-explore.md` — Explore skill: thinking partner, no code written.
- `skills/opsx-apply.md` — Apply skill: implement tasks from the checklist.
- `skills/opsx-archive.md` — Archive skill: finalize and move a change to archive.

### codepi/templates/

**`adapters.py`** — Tool-specific command file formatters.

- `ToolAdapter` — ABC with `tool_id`, `get_file_path(command_id)`, `format_file(CommandContent)`.
- `ClaudeAdapter` / `CursorAdapter` / `WindsurfAdapter` — Concrete formatters for each AI tool's command file conventions.
- `CommandContent(id, name, description, category, tags, body)` — Dataclass holding the content to format.
- `ADAPTERS` — Dict mapping tool IDs to adapter instances.

**`registry.py`** — Template registry for workflow skill → command file generation.

- `WorkflowTemplate(skill, command_id, command_tags, command_category)` — Dataclass pairing a `Skill` with its generated command metadata.
- `TemplateRegistry(skills_dirs)` — Loads skills, filters those with `workflow:` frontmatter, generates command files.
- `TemplateRegistry.load_workflows()` — Scans skills dirs for `workflow:` metadata, returns `dict[str, WorkflowTemplate]`.
- `TemplateRegistry.generate_commands(tool_id, output_dir)` — Generates command files for the specified tool. Returns list of generated `Path`s.
- `TemplateRegistry.validate_parity()` — Checks all workflow skills have non-empty bodies and required metadata.

**`cli.py`** — CLI subcommand for `codepi template`.

- `add_template_parser(subparsers)` — Adds `template` subparser to an argparse parser.
- `run_template_cmd(args)` — Dispatches to `list`, `generate`, or `validate` subcommands.

**`artifacts/`** — OpenSpec artifact templates.

- `TEMPLATES` — Dict mapping artifact IDs (`"proposal"`, `"spec"`, `"design"`, `"tasks"`) to template content strings.
- Templates are loaded at import time from the bundled `.md` files.

### codepi/tui/

**`renderer.py`** — Terminal output.

- `StreamingRenderer(console)` — Wraps a `rich.Console`. Methods: `start_turn()`, `append_token(token)`, `end_turn()`, `render_tool_call(name, args)`, `render_tool_result(name, content)`, `render_user_message(text)`, `render_error(message)`, `render_info(message)`.

**`components.py`** — Input widgets.

- `make_keybindings(on_follow_up, on_cancel, on_clear, on_checkpoint)` — Returns a `prompt_toolkit.KeyBindings` object with all interactive shortcuts wired up.
- `default_toolbar(model, session_id)` — Returns an HTML toolbar for the prompt session bottom bar.

**`app.py`** — Combines renderer and input into a complete TUI.

- `TUIApp(model, session_id, ...)` — Holds a `StreamingRenderer` and a `prompt_toolkit.PromptSession`. Call `get_input(prompt)` to await user input.

### codepi/modes/

**`interactive.py`** — `InteractiveMode` — The default user-facing mode. Wires `TUIApp` and `AgentSession` together.

**`print_mode.py`** — `PrintMode` — Single-shot mode. Writes all output to an `IO[str]` (defaults to `sys.stdout`).

**`rpc.py`** — `RPCMode` — JSONL subprocess protocol. See [RPC Protocol](#rpc-protocol).

**`sdk.py`** — `SDK` — Embeddable Python API. See [SDK Usage](#sdk-usage).

---

## Architecture Walkthrough: OpenSpec Core Profile as a Worked Example

This section walks through how the OpenSpec core profile (`/opsx:propose`, `/opsx:explore`, `/opsx:apply`, `/opsx:archive`) is implemented in mypi using the skill-driven architecture. It demonstrates how all the core systems — `SkillLoader`, `TemplateRegistry`, `ToolAdapter`, and `AgentSession` — work together.

### Design: Skill-Driven Architecture

The OpenSpec core profile uses a **pure skill-driven** approach:

1. **Skills are the implementation.** Each command is a skill file in `mypi/extensions/openspec/skills/`. The skill body contains all the instructions the LLM follows.
2. **No Python execution.** The LLM creates files and directories directly using the `write`, `bash`, and `edit` tools — no `ChangeManager` or CLI needed.
3. **Filesystem as state.** The LLM reads the directory structure to determine what artifacts exist and what needs to be created.

### Component 1: Skill Files (`mypi/extensions/openspec/skills/`)

Each skill is a markdown file with YAML frontmatter:

```markdown
---
name: opsx-propose
description: Propose a new change - create it and generate all artifacts in one step
category: Workflow
tags: [openspec, change, workflow]
workflow: opsx-propose
command_id: opsx-propose
---

Propose a new change - create the change and generate all artifacts in one step.
...
```

The `workflow:` key marks it as a workflow skill. The `command_id:` key controls the output filename for template generation.

### Component 2: Package Skill Discovery (`skill_loader.py`)

The OpenSpec skills live in the package, not in `~/.mypi/skills/`. At startup:

```python
# __main__.py
package_skills = Path(__file__).parent / "extensions" / "openspec" / "skills"
SkillLoader.set_package_skills_dir(package_skills)
skill_loader = SkillLoader([config.paths.skills_dir])
```

`set_package_skills_dir()` prepends the package path so package skills take priority over user skills with the same name. When the LLM sees `/opsx:propose`, the routing logic in `AgentSession` looks up `opsx-propose` via `skill_loader.load_skill_content()`.

### Component 3: Template Generation (`mypi/templates/`)

The template system reads workflow skills and generates slash command files:

```bash
mypi template generate --tool claude
```

This flow:

1. `TemplateRegistry.load_workflows()` — `SkillLoader` scans skills dirs. Skills with `workflow:` metadata are collected into `WorkflowTemplate` objects.
2. For each `WorkflowTemplate` — the `ClaudeAdapter` formats the skill body into Claude Code's convention (markdown with heading). `get_file_path(command_id)` returns `.claude/commands/opsx-propose.md`.
3. Files are written to the output directory.

The `command_id` frontmatter field controls the output filename. Without it, the skill `name` would be used. This lets skills have a descriptive internal name (`opsx-propose`) while controlling the public-facing command name.

### Component 4: Slash Command Routing (`agent_session.py`)

When the user types `/opsx:propose add-dark-mode`, `AgentSession.prompt()` intercepts it:

```python
def _is_opsx_command(self, text: str) -> bool:
    return text.strip().startswith("/opsx:") and len(text.strip()) > 6

def _handle_opsx_command(self, text: str) -> str:
    prefix = "/opsx:"
    rest = text.strip()[len(prefix):]          # "propose add-dark-mode"
    command, args = rest.split(" ", 1) if " " in rest else (rest, "")
    skill_name = f"opsx-{command}"              # "opsx-propose"
    skill = self._skill_loader.load_skill_content(skill_name)
    return (
        f"--- Skill: {skill.name} ---\n\n"
        f"{skill.body}\n\n"
        f"--- User Request ---\n\n{args}"
    )
```

The result is injected as the user's message. The LLM sees the skill instructions followed by the user's request, and follows the skill's step-by-step guidance to create the change.

### Component 5: Artifact Templates (`mypi/templates/artifacts/`)

The OpenSpec skills reference artifact templates for structure. The `proposal.md` template, for example:

```markdown
## Why

<!-- Explain the motivation for this change. What problem does this solve? Why now? -->

## What Changes

<!-- Describe what will change. Be specific about new capabilities... -->

## Capabilities

### New Capabilities
<!-- Each creates specs/<name>/spec.md. Use kebab-case names. -->
- `<name>`: <brief description>

### Modified Capabilities
<!-- Existing capabilities whose REQUIREMENTS are changing... -->
- `<existing-name>`: <what requirement is changing>

## Impact
<!-- Affected code, APIs, dependencies, systems -->
```

Skills reference these as structure guides. The LLM uses the template headers as section names to fill in, creating consistent artifacts across changes.

### Data Flow Summary

```
User types "/opsx:propose add-dark-mode"
            │
            ▼
AgentSession._is_opsx_command() ────► False ──► Normal turn processing
            │ True
            ▼
AgentSession._handle_opsx_command()
  → skill_loader.load_skill_content("opsx-propose")
  → Returns skill body + user args
            │
            ▼
LLM sees skill instructions + "add-dark-mode"
  → Follows step-by-step guidance
  → Uses write/bash/edit tools
  → Creates openspec/changes/add-dark-mode/
      ├── .openspec.yaml
      ├── proposal.md
      ├── specs/ui-theme/spec.md
      ├── design.md
      └── tasks.md
            │
            ▼
mypi template generate --tool claude
  → TemplateRegistry.load_workflows()
  → Finds opsx-propose.md (workflow: opsx-propose)
  → ClaudeAdapter writes .claude/commands/opsx-propose.md
  → Now works as a native Claude Code slash command
```

### Key Design Decisions in This Implementation

| Decision | Rationale |
|---|---|
| Skills as the only implementation | Simplest possible architecture — no duplicate CLI logic, fully testable via skill content |
| Filesystem as state | LLM reads directory structure directly — no schema loader needed, no API calls |
| Package-managed skills | Skills ship with mypi and are always available; user skills in `~/.mypi/skills/` override if needed |
| `command_id` decoupled from skill `name` | Skill internal name can be descriptive (`opsx-propose`) while output filename is clean |
| Skill routing in `prompt()` | Clean interception before the message enters the turn — no changes to `_run_turn()` |

---

## Extension API

### Writing a Python extension

Place a `.py` file in `~/.mypi/extensions/`. The file must define at least one non-abstract subclass of `Extension`. The loader instantiates every such class it finds.

A minimal extension:

```python
# ~/.mypi/extensions/my_extension.py
from codepi.extensions.base import Extension
from codepi.core.events import BeforeAgentStartEvent

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
from codepi.tools.base import ToolResult

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
from codepi.extensions.base import Extension
from codepi.tools.base import Tool, ToolResult

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
from codepi.extensions.base import Extension, UIComponents

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

Skills are `.md` files with YAML frontmatter. They are loaded from `~/.mypi/skills/` (and any additional `--skills-dir` directories).

**File format:**

```markdown
---
name: <identifier>
description: <when-to-use description shown before the skill body>
compatibility: <optional metadata>
---

<Skill body — plain Markdown. Can contain headers, lists, code blocks.>
```

**Workflow skills** — skills with `workflow:` frontmatter — are treated differently. They drive the template system for generating slash command files:

```markdown
---
name: my-workflow
description: Do a thing
category: Workflow
tags: [workflow, example]
workflow: my-workflow          # Marks this as a workflow skill
command_id: my-workflow       # Output filename for command file generation
---

## Step 1: Do the thing
...
```

| Field | Required | Description |
|---|---|---|
| `name` | yes | Skill identifier (shown in system prompt) |
| `description` | yes | When-to-use guidance |
| `workflow` | no | If present, marks skill as a workflow skill for template generation |
| `command_id` | no | Filename for generated command file (defaults to `name` if omitted) |
| `category` | no | Category tag for command file metadata |
| `tags` | no | List of tags for command file metadata |

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

**How injection works (lazy loading):**

At startup, `SkillLoader.inject_skills()` appends only the metadata to the system prompt:

```
---
# Available Skills

## Skill: <name>
**When to use:** <description>

## Skill: <name2>
...
```

The body content is **not** included in the system prompt. When the LLM determines a skill is relevant, it calls the `skill` tool with the skill name, and `SkillLoader.load_skill_content()` returns the full body.

This keeps the system prompt lean while still making skill instructions available when needed.

**Parser behaviour:**

- File must start with exactly `---` on the first line.
- The closing `---` must appear on its own line.
- Frontmatter is parsed with `yaml.safe_load`.
- Files missing `name` in frontmatter are silently skipped.
- Files that fail YAML parsing are silently skipped.
- `metadata` field exposes the raw YAML dict for programmatic access.

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

**`get-session-id`** — Get the current session ID. Emits an `id` event.

```json
{"type": "get-session-id"}
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

**`id`** — Response to `get-session-id` command. Contains the current session UUID.

```json
{"type": "id", "id": "550e8400-e29b-41d4-a716-446655440000"}
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
from codepi.config import load_config
from codepi.ai.openai_compat import OpenAICompatProvider
from codepi.core.session_manager import SessionManager
from codepi.tools.builtins import make_builtin_registry
from codepi.modes.sdk import SDK

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
    skill_loader=skill_loader,  # enables /opsx: command routing
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
from codepi.extensions.base import Extension
from codepi.core.events import BeforeAgentStartEvent

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
    skill_loader=skill_loader,  # enables /opsx: command routing
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
    from codepi.tools.base import ToolRegistry
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
├── templates/
│   ├── test_artifacts.py     # OpenSpec artifact template content validation
│   └── test_registry.py       # TemplateRegistry and adapter format tests
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
