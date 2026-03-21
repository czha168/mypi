# mypi User Guide

## Table of Contents

1. [What is mypi](#what-is-mypi)
2. [Installation](#installation)
3. [Configuration](#configuration)
   - [Config file structure](#config-file-structure)
   - [Environment variables](#environment-variables)
   - [All options](#all-options)
4. [Operation Modes](#operation-modes)
   - [Interactive mode](#interactive-mode)
   - [Print mode](#print-mode)
   - [RPC mode](#rpc-mode)
   - [SDK mode](#sdk-mode)
5. [Built-in Tools](#built-in-tools)
6. [Skills](#skills)
   - [Creating a skill](#creating-a-skill)
   - [Using skills](#using-skills)
   - [Workflow skills and the template system](#workflow-skills-and-the-template-system)
7. [Template Generation](#template-generation)
   - [Command files for Claude Code, Cursor, and Windsurf](#command-files-for-claude-code-cursor-and-windsurf)
8. [OpenSpec Core Profile](#openspec-core-profile)
   - [The four commands](#the-four-commands)
   - [How it works](#how-it-works)
   - [Example session](#example-session)
9. [Session Management](#session-management)
   - [How sessions work](#how-sessions-work)
   - [Resuming a session](#resuming-a-session)
   - [Branches](#branches)
   - [Auto-compaction](#auto-compaction)
8. [Common Workflows](#common-workflows)

---

## What is mypi

mypi is a minimalist, terminal-based coding assistant written in Python. It connects to any OpenAI-compatible LLM API and gives the model a set of file system and shell tools to read, edit, and run code on your behalf.

The design philosophy is deliberate minimalism: the core ships with exactly seven tools and a simple extension system. There are no built-in sub-agents, no planning modes, and no workflow automation. If you need those, you add them as extensions or skills.

mypi runs as a standard CLI program. It reads your question, sends it to the LLM along with any relevant tool calls, and streams the response back to your terminal.

---

## Installation

mypi requires Python 3.11 or later.

**From source:**

```bash
git clone <repository-url>
cd mypi
pip install -e .
```

**With development dependencies (for running tests):**

```bash
pip install -e ".[dev]"
```

After installation the `mypi` command is available on your PATH.

**Runtime dependencies installed automatically:**

| Package | Purpose |
|---|---|
| `openai>=1.0` | LLM API client |
| `rich>=13.0` | Terminal rendering |
| `prompt_toolkit>=3.0` | Interactive input |
| `watchdog>=4.0` | Extension hot-reload |
| `pyyaml>=6.0` | Skill file parsing |

---

## Configuration

### Config file structure

mypi looks for a configuration file at `~/.mypi/config.toml` by default. If the file does not exist, all defaults apply. You can specify a different path with `--config PATH`.

A complete config file:

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

You only need to include the keys you want to change from the defaults.

### Environment variables

Two environment variables are checked before the config file:

| Variable | Overrides |
|---|---|
| `OPENAI_API_KEY` | `provider.api_key` |
| `OPENAI_BASE_URL` | `provider.base_url` |

Environment variables take precedence over `config.toml`. This is useful for CI environments or when you have multiple API keys.

```bash
export OPENAI_API_KEY=sk-...
mypi
```

### All options

**`[provider]` section**

| Key | Default | Description |
|---|---|---|
| `base_url` | `https://api.openai.com/v1` | Base URL for any OpenAI-compatible API. Point to Ollama, Groq, Azure OpenAI, etc. |
| `api_key` | `""` | API key. Set via env var for safety. |
| `model` | `gpt-4o` | Default model name. Can be overridden per invocation with `--model`. |

**`[session]` section**

| Key | Default | Description |
|---|---|---|
| `compaction_threshold` | `0.80` | Fraction of the context window at which automatic compaction triggers (0.0–1.0). |
| `max_retries` | `3` | Number of retry attempts on transient API errors before giving up. |

**`[paths]` section**

| Key | Default | Description |
|---|---|---|
| `sessions_dir` | `~/.mypi/sessions` | Directory where session JSONL files are stored. |
| `skills_dir` | `~/.mypi/skills` | Directory scanned for `.md` skill files. |
| `extensions_dir` | `~/.mypi/extensions` | Directory scanned for `.py` extension files. |

All path values support `~` expansion.

**Using a different API provider:**

```toml
[provider]
base_url = "http://localhost:11434/v1"  # Ollama
api_key  = "ollama"
model    = "codellama"
```

---

## Operation Modes

### Interactive mode

The default mode. Run `mypi` with no flags to start an interactive session.

```bash
mypi
```

You get a prompt (`> `) at the bottom of the terminal. Type your question and press Enter. The assistant response streams to the screen in real time. Tool calls are shown inline as they execute.

**Keyboard shortcuts:**

| Key | Action |
|---|---|
| `Enter` | Submit current input |
| `Alt+Enter` | Queue input as a follow-up (runs after current turn completes) |
| `Escape` | Cancel current request |
| `Ctrl+L` | Clear the terminal |
| `Ctrl+S` | Checkpoint (saves session state) |
| `Ctrl+C` | Exit |

The bottom toolbar always shows the current model name, the first 8 characters of the session ID, and a key reference.

**Command-line flags for interactive mode:**

```bash
mypi --model gpt-4o-mini        # override model for this session
mypi --session <SESSION_ID>     # resume an existing session
mypi --skills-dir ./my-skills   # add an extra skills directory
mypi --config ./project.toml    # use a project-local config file
```

### Print mode

Print mode sends a single prompt, streams the response to stdout, and exits. Designed for scripting and automation.

```bash
mypi --print "Summarize the file README.md"
```

Tool calls and their results are also written to stdout in a compact format:

```
[tool: read] {'path': 'README.md'}
[result: read] # My Project...
```

Combine with shell pipes and redirects as usual:

```bash
mypi --print "List all Python files in src/" > file_list.txt
mypi --print "Fix the bug in src/parser.py" 2>&1 | tee fix.log
```

All other flags (`--model`, `--session`, `--skills-dir`, etc.) work in print mode.

### RPC mode

RPC mode runs mypi as a long-lived subprocess that accepts commands on stdin and emits events on stdout, both as newline-delimited JSON. Use this to integrate mypi into editors, IDEs, or other tools.

```bash
mypi --rpc
```

**Commands (send to stdin):**

```json
{"type": "prompt", "text": "What does main.py do?"}
{"type": "steer", "text": "Focus on error handling only"}
{"type": "follow_up", "text": "Now explain the tests"}
{"type": "cancel"}
{"type": "get-session-id"}
{"type": "exit"}
```

**Events (emitted to stdout):**

```json
{"type": "token", "text": "The main"}
{"type": "token", "text": " function..."}
{"type": "tool_call", "name": "read", "arguments": {"path": "main.py"}}
{"type": "tool_result", "name": "read", "content": "import asyncio..."}
{"type": "error", "message": "Failed after 3 attempts: ..."}
{"type": "done", "usage": {}}
{"type": "cancelled"}
{"type": "id", "id": "550e8400-e29b-41d4-a716-446655440000"}
```

A `done` event is emitted after each `prompt`, `steer`, or `follow_up` command completes.

**The `steer` command** injects a correction mid-turn. If a tool call is currently executing, its result is replaced with the steer text. If no tool call is in flight, steer behaves identically to `follow_up`.

**The `get-session-id` command** returns the current session ID. It emits an `id` event with the session UUID.

### SDK mode

The SDK is a Python API for embedding mypi inside another Python application. It is not exposed as a CLI mode; import it directly.

```python
import asyncio
from pathlib import Path
from mypi.config import load_config
from mypi.ai.openai_compat import OpenAICompatProvider
from mypi.core.session_manager import SessionManager
from mypi.tools.builtins import make_builtin_registry
from mypi.modes.sdk import SDK

async def main():
    config = load_config()
    provider = OpenAICompatProvider(
        base_url=config.provider.base_url,
        api_key=config.provider.api_key,
        default_model=config.provider.model,
    )
    sm = SessionManager(sessions_dir=config.paths.sessions_dir)
    sm.new_session(model=config.provider.model)
    registry = make_builtin_registry()

    sdk = SDK(provider=provider, session_manager=sm,
              model=config.provider.model, tool_registry=registry)

    # Full response at once
    response = await sdk.prompt("What files are in the current directory?")
    print(response)

    # Streaming tokens
    async for token in sdk.stream("Explain the first file"):
        print(token, end="", flush=True)

asyncio.run(main())
```

---

## Built-in Tools

mypi ships with seven built-in tools. The LLM chooses which tools to invoke based on the conversation context.

### `read`

Read a file's contents.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `path` | string | yes | Absolute or relative file path |
| `offset` | integer | no | 1-based line number to start reading from |
| `limit` | integer | no | Maximum number of lines to return |

Example: read lines 10–30 of a file:
```
path="src/main.py", offset=10, limit=20
```

### `write`

Write content to a file, creating it or overwriting it entirely. Parent directories are created automatically.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `path` | string | yes | File path to write |
| `content` | string | yes | Complete file content |

### `edit`

Replace one occurrence of a string in a file. Fails if `old_string` is not found or appears more than once (to prevent accidental multi-site edits).

| Parameter | Type | Required | Description |
|---|---|---|---|
| `path` | string | yes | File to edit |
| `old_string` | string | yes | Exact text to find (must be unique in the file) |
| `new_string` | string | yes | Replacement text |

### `bash`

Execute a shell command. stdout and stderr are merged and returned.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `command` | string | yes | Shell command to run |
| `timeout` | number | no | Seconds before the command is killed (default: 30) |

Returns the exit code in the error field if non-zero. Use `timeout` for commands that might hang.

### `find`

Find files matching a glob pattern, sorted by modification time (newest first).

| Parameter | Type | Required | Description |
|---|---|---|---|
| `path` | string | yes | Directory to search in |
| `pattern` | string | yes | Glob pattern, e.g. `*.py` |

Searches recursively through all subdirectories.

### `grep`

Search file contents for a regex pattern. Uses `rg` (ripgrep) if available on PATH, otherwise falls back to Python's `re` module.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `pattern` | string | yes | Regex pattern |
| `path` | string | yes | Directory or file to search |
| `glob` | string | no | File glob filter, e.g. `*.py` |

Returns matches in `file:line: content` format.

### `ls`

List directory contents with metadata. Use `.` for the current directory.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `path` | string | yes | Directory to list (use `.` for current directory) |

Returns each entry with its type (`file`/`dir`), size in bytes, modification timestamp, and name.

### `skill`

Load a skill's full content by name. Call this when you want to apply a specific skill's instructions.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name` | string | yes | Name of the skill to load |

Example: `skill(name="commit-message")` returns the full body of the commit-message skill.

The LLM sees skill names and descriptions at startup. This tool loads the full content when the LLM determines the skill is relevant.

---

## Skills

Skills are reusable instruction sets injected into the system prompt. They tell the LLM how to approach specific types of tasks — for example, "when asked to write tests, always use pytest fixtures" or "when reviewing code, check these specific things."

Skills use the same Markdown format as Claude Code slash commands.

### Creating a skill

Create a `.md` file in your skills directory (`~/.mypi/skills/` by default). The file must start with YAML frontmatter.

```markdown
---
name: write-tests
description: Write pytest tests for Python code
---

When writing tests:

1. Use `pytest` with `pytest-asyncio` for async code.
2. Put fixtures in `conftest.py`, not in the test file.
3. Name test functions `test_<what>_<expected_outcome>`.
4. Each test should cover one behavior only.
5. Use `tmp_path` for file system tests.

Always run the tests with `bash` tool after writing them to confirm they pass.
```

**Frontmatter fields:**

| Field | Required | Description |
|---|---|---|
| `name` | yes | Skill identifier (used in the system prompt heading) |
| `description` | yes | When-to-use guidance shown before the skill body |
| `compatibility` | no | Optional metadata (not currently enforced) |

### Using skills

Skills are loaded automatically at startup from `~/.mypi/skills/`. All `.md` files in the directory that have valid frontmatter are loaded.

You can add extra skill directories:

```bash
mypi --skills-dir ./project-skills --skills-dir ~/shared-skills
```

All directories are merged. The default `~/.mypi/skills/` is always included.

**Lazy loading:** At startup, only skill metadata (name and description) is injected into the system prompt. This keeps the prompt lean. When the LLM determines a skill is relevant, it can invoke the `skill` tool to load the full content on-demand.

Skills are injected once at the start of each turn under a "# Available Skills" heading in the system prompt:

```
# Available Skills

## Skill: commit-message
**When to use:** Write a git commit message after making code changes
```

The `skill` tool loads full content when called:

```
skill(name="commit-message")
→ Returns the full skill body with all instructions
```

### Workflow skills and the template system

Skills with `workflow:` frontmatter are treated as **workflow skills**. The template system reads them and generates slash command files for external AI tools (Claude Code, Cursor, Windsurf).

```markdown
---
name: opsx-propose
description: Propose a new change - create it and generate all artifacts
category: Workflow
tags: [openspec, change]
workflow: opsx-propose       # Marks this as a workflow skill
command_id: opsx-propose    # Output filename for command generation
---

Propose a new change...
```

Two metadata fields enable workflow skills:

| Field | Purpose |
|---|---|
| `workflow` | Identifies the skill as a workflow skill (template system reads this key) |
| `command_id` | The filename for the generated command file (e.g., `opsx-propose` → `.claude/commands/opsx-propose.md`) |

Package-managed workflow skills are bundled in `mypi/extensions/openspec/skills/` and loaded automatically. See [OpenSpec Core Profile](#openspec-core-profile) for the built-in workflow skills.

---

## Template Generation

The template system generates slash command files from workflow skills. This lets mypi's workflow skills work as native slash commands in Claude Code, Cursor, and Windsurf.

### Command files for Claude Code, Cursor, and Windsurf

Generate command files for all three tools:

```bash
mypi template generate --tool claude
mypi template generate --tool cursor
mypi template generate --tool windsurf
```

Each tool has its own conventions:

| Tool | Output directory | Format |
|---|---|---|
| Claude Code | `.claude/commands/` | Markdown with `# Command Name` heading |
| Cursor | `.cursor/rules/` | YAML frontmatter + Markdown body |
| Windsurf | `.windsurfrules/` | Plain text with description |

Generated files contain the full skill body from the workflow skill. Running `/opsx:propose` in Claude Code will invoke the same instructions as typing it in mypi.

List available templates:

```bash
mypi template list
```

Validate that all workflow skills have complete content:

```bash
mypi template validate
```

---

## OpenSpec Core Profile

mypi ships with four built-in workflow skills that implement the [OpenSpec](https://github.com/Fission-AI/OpenSpec) core profile. These skills guide the LLM through a structured change workflow: propose → explore → apply → archive.

### The four commands

| Command | Purpose |
|---|---|
| `/opsx:propose` | Create a new change with planning artifacts (proposal, specs, design, tasks) |
| `/opsx:explore` | Think through ideas, investigate problems, clarify requirements — no code written |
| `/opsx:apply` | Implement tasks from the checklist, marking each complete as you go |
| `/opsx:archive` | Finalize a completed change by moving it to the archive |

These commands are available in mypi's interactive, print, and RPC modes. They also work as slash commands in Claude Code, Cursor, and Windsurf after running `mypi template generate --tool <tool>`.

### How it works

The OpenSpec skills use a **change directory** structure:

```
openspec/
└── changes/
    └── <change-name>/           # e.g., add-dark-mode
        ├── .openspec.yaml       # Metadata (schema, created date)
        ├── proposal.md           # Why & what
        ├── specs/
        │   └── <capability>/    # Per-capability requirements
        │       └── spec.md
        ├── design.md             # How (technical decisions)
        └── tasks.md             # Implementation checklist
```

State is determined by **filesystem existence** — the LLM reads the directory to know which artifacts exist and which are still needed.

### Example session

**Step 1 — Propose a change:**

```
> /opsx:propose add-dark-mode

You: Add a dark mode toggle to the settings page

[LLM creates openspec/changes/add-dark-mode/ with all artifacts]

## Change Created: add-dark-mode

Location: openspec/changes/add-dark-mode/
Artifacts:
- proposal.md ✓
- specs/ui-theme/spec.md ✓
- design.md ✓
- tasks.md ✓ (8 tasks)

Ready for implementation. Run /opsx:apply to start working.
```

**Step 2 — Explore (optional):**

```
> /opsx:explore

You: I want to improve the auth flow

[LLM investigates the codebase, asks questions, draws diagrams]
[Offers to capture decisions in artifacts when ready]
```

**Step 3 — Implement:**

```
> /opsx:apply add-dark-mode

Implementing change: add-dark-mode

Working on task: 1.1 Create ThemeContext
[...implementation...]
✓ Task complete

Working on task: 1.2 Add CSS custom properties
✓ Task complete

## Implementation Progress: add-dark-mode
Tasks completed: 2/8
```

**Step 4 — Archive:**

```
> /opsx:archive add-dark-mode

[LLM checks artifacts and tasks]

Warning: 1 task not complete:
- [ ] 3.2 Add accessibility tests

Archive anyway? (yes/no)

You: yes

## Archive Complete ✓

Change: add-dark-mode
Archived to: openspec/changes/archive/2026-03-20-add-dark-mode/
```

---

## Session Management

### How sessions work

Every mypi run is associated with a session. A session is a single JSONL file stored in `~/.mypi/sessions/`. Each line in the file is a JSON object called a session entry.

A new session is created automatically when you start mypi without `--session`. The session ID (a UUID) is shown in the terminal toolbar.

Session entries are written append-only as the conversation progresses. The types of entries are:

| Type | Description |
|---|---|
| `session_info` | Header entry, written once at session creation. Contains version, model, and creation timestamp. |
| `message` | A conversation message. The `role` field is `user`, `assistant`, or `tool`. |
| `compaction` | A context summary written by auto-compaction. Replaces earlier messages when building context. |
| `custom` | Written by extensions for their own purposes. |

### Resuming a session

Pass the session ID to `--session`:

```bash
mypi --session 550e8400-e29b-41d4-a716-446655440000
```

You can list available sessions by listing files in `~/.mypi/sessions/`:

```bash
ls ~/.mypi/sessions/
```

### Branches

Sessions have a tree structure. Each entry has a `parentId` pointing to the previous entry. When you resume a session that has multiple leaf nodes (branches), mypi lists them and asks you to pick one:

```
Session has 2 branches. Select one to resume:

  [1] depth=5  Here is the refactored version of parse...
  [2] depth=3  I can also take a different approach...

Enter branch number (1-2):
```

Branching is currently managed internally by extensions or via the `SessionManager.branch()` API. The interactive UI does not expose a manual branch command.

### Auto-compaction

When the number of input tokens approaches `compaction_threshold` × context window size (default: 80% of 128,000 tokens), mypi automatically summarizes the conversation. The summary is written as a `compaction` entry. On the next turn, older messages are discarded and replaced by the summary, keeping the context within bounds without losing important history.

The compaction summary is generated by the same model using a dedicated prompt. It preserves key decisions, file names, and code changes discussed.

---

## Common Workflows

**Explore a new codebase:**

```
> What is the structure of this project? Start from the root directory.
```

**Fix a specific bug:**

```
> The test in tests/core/test_session_manager.py is failing. Find the bug and fix it.
```

**Write a new feature:**

```
> Add a --list-sessions flag to the CLI that prints all session IDs and their creation dates.
```

**Run in a CI pipeline:**

```bash
mypi --print "Run the test suite and report any failures" \
     --model gpt-4o \
     --config ./ci-config.toml
```

**Use a local model via Ollama:**

```bash
OPENAI_BASE_URL=http://localhost:11434/v1 \
OPENAI_API_KEY=ollama \
mypi --model codellama
```

**Chain multiple prompts in a script:**

```bash
SESSION=$(python -c "import uuid; print(uuid.uuid4())")
mypi --print "Audit src/ for security issues" --session $SESSION
mypi --print "Fix the issues you found" --session $SESSION
```
