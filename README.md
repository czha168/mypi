# codepi

A minimalist terminal-based coding assistant written in Python. Give it a task, it uses file system and shell tools to read, edit, and execute code on your behalf.

Inspired by [pi-coding-agent](https://github.com/badlogic/pi-mono/tree/main/packages/coding-agent).

## Features

- **12 built-in tools**: read, write, edit, bash, find, grep, ls + 5 LSP-powered tools
- **4 operation modes**: interactive TUI, print mode, RPC mode, Python SDK
- **Session persistence**: Tree-structured JSONL with branching and auto-compaction
- **Extensible**: Python extensions + Claude Code-compatible skills
- **Any LLM**: Works with any OpenAI-compatible endpoint (Ollama, Groq, LM Studio, etc.)
- **LSP support**: Python language server integration for semantic code intelligence

## Installation

```bash
pip install -e .
```

Requires Python 3.11+.

## Quick Start

```bash
# Set your API key
export OPENAI_API_KEY=sk-...

# Start an interactive session
codepi
```

### Installing an LSP Server (Recommended)

For LSP tools to work, you need a Python language server installed. codepi will auto-detect any of these servers:

| Server | Installation | Notes |
|--------|--------------|-------|
| **pyright** (recommended) | `npm install -g pyright` or `pip install pyright` | Fast, excellent type inference |
| **pylsp** | `pip install python-lsp-server[all]` | Feature-rich, many plugins |
| **jedi-language-server** | `pip install jedi-language-server` | Lightweight, good completion |

To specify a server explicitly, set it in your config:

```toml
[lsp]
server = "pyright"
```

If no server is found, LSP tools will return a helpful error message with installation instructions.

## Configuration

Create `~/.codepi/config.toml`:

```toml
[provider]
base_url = "https://api.openai.com/v1"
api_key  = ""
model    = "gpt-4o"

[session]
compaction_threshold = 0.50
max_retries = 3

[lsp]
server = ""      # "pyright", "pylsp", "jedi-language-server", or empty for auto-detect
enabled = true   # Set to false to disable LSP tools

[security]
enabled = true

[memory]
enabled = true
max_items = 500
injection_token_budget = 1000
hotness_half_life_days = 7
dedup_jaccard_threshold = 0.7
```

**Environment variables** (override config):

```bash
export OPENAI_API_KEY=sk-...
export OPENAI_BASE_URL=http://localhost:11434/v1  # Ollama
codepi --model codellama
```

## Usage Modes

### Interactive Mode (default)

```bash
codepi
```

Full terminal UI with streaming output, tool call display, and keyboard shortcuts.

| Key | Action |
|-----|--------|
| `Enter` | Submit message |
| `Alt+Enter` | Queue follow-up |
| `Escape` | Cancel |
| `Ctrl+L` | Clear |
| `Ctrl+C` | Exit |

### Print Mode

Script-friendly single-shot mode:

```bash
codepi --print "List Python files in src/"
codepi --print "Fix the bug in parser.py" 2>&1 | tee fix.log
```

### RPC Mode

Integrate into editors/IDEs via JSONL stdin/stdout:

```bash
codepi --rpc
```

```json
{"type": "prompt", "text": "What does main.py do?"}
{"type": "tool_call", "name": "read", "arguments": {"path": "main.py"}}
{"type": "tool_result", "name": "read", "content": "..."}
```

### Python SDK

Embed in your application:

```python
from codepi.modes.sdk import SDK
from codepi.ai.openai_compat import OpenAICompatProvider
from codepi.core.session_manager import SessionManager
from codepi.tools.builtins import make_builtin_registry

provider = OpenAICompatProvider(base_url="...", api_key="...")
sm = SessionManager("~/.codepi/sessions")
sm.new_session(model="gpt-4o")

sdk = SDK(provider=provider, session_manager=sm, model="gpt-4o", 
          tool_registry=make_builtin_registry())

response = await sdk.prompt("List files in the current directory")
```

## Built-in Tools

| Tool | Description |
|------|-------------|
| `read` | Read file contents with optional line offset/limit |
| `write` | Write/overwrite entire file |
| `edit` | Replace unique string in file |
| `bash` | Execute shell command with timeout |
| `find` | Glob pattern file search |
| `grep` | Regex content search (uses ripgrep if available) |
| `ls` | Directory listing with metadata |

## LSP Tools

codepi includes 5 LSP-powered tools for semantic Python code intelligence. These tools communicate with a Python language server (pyright, pylsp, or jedi-language-server) to provide intelligent code navigation and analysis.

| Tool | Description |
|------|-------------|
| `lsp_goto_definition` | Jump to the definition of a symbol at a given position |
| `lsp_find_references` | Find all references to a symbol across the workspace |
| `lsp_diagnostics` | Get type errors, warnings, and hints for a file |
| `lsp_hover` | Get type information and documentation for a symbol |
| `lsp_rename` | Rename a symbol across all references in the workspace |

### LSP Tool Parameters

**`lsp_goto_definition`**
```json
{
  "file_path": "/path/to/file.py",  // Absolute path
  "line": 10,                        // 1-based line number
  "character": 5                     // 0-based character offset
}
```

**`lsp_find_references`**
```json
{
  "file_path": "/path/to/file.py",
  "line": 10,
  "character": 5,
  "include_declaration": true        // Include symbol's own declaration
}
```

**`lsp_diagnostics`**
```json
{
  "file_path": "/path/to/file.py",
  "severity": "error"                // "error", "warning", "information", "hint", or "all"
}
```

**`lsp_hover`**
```json
{
  "file_path": "/path/to/file.py",
  "line": 10,
  "character": 5
}
```

**`lsp_rename`**
```json
{
  "file_path": "/path/to/file.py",
  "line": 10,
  "character": 5,
  "new_name": "better_name",
  "dry_run": true                    // Preview changes without applying
}
```

## Extensions

Drop `.py` files into `~/.codepi/extensions/`:

```python
from codepi.extensions.base import Extension
from codepi.core.events import BeforeAgentStartEvent

class MyExtension(Extension):
    name = "my-extension"
    
    async def on_before_agent_start(self, event: BeforeAgentStartEvent):
        return BeforeAgentStartEvent(
            system_prompt=event.system_prompt + "\n\nBe concise.",
            messages=event.messages,
        )
```

Extensions can:
- Hook into lifecycle events (before/after tool calls, session changes)
- Register custom tools
- Add keyboard shortcuts and UI components
- Hot-reload on file change

## Skills

Markdown files with YAML frontmatter, injected into system prompt:

```markdown
---
name: commit-message
description: Write a git commit message after making code changes
---

When writing commits:
1. Use imperative mood, 50 chars max
2. Explain *why*, not *what*
```

Place in `~/.codepi/skills/` or add directories with `--skills-dir`.

## Session Management

Sessions are stored as JSONL files in `~/.codepi/sessions/`. Resume with:

```bash
codepi --session 550e8400-e29b-41d4-a716-446655440000
```

**Auto-compaction** triggers at 50% context window usage — the model summarizes conversation history to free up tokens. Compaction produces two tiers: a short keyword abstract (L0) and a structured overview (L1), enabling context-aware reconstruction based on available token budget.

**Branching** allows exploring alternative approaches. The session tree preserves history for each branch.

## Cross-Session Memory

codepi automatically extracts reusable knowledge from conversations and persists it across sessions. After each auto-compaction, a memory extraction pipeline:

1. **Extracts** knowledge items from the compacted conversation (decisions, patterns, file-knowledge, preferences)
2. **Deduplicates** against existing memories using content hashing and Jaccard similarity
3. **Stores** unique items in `~/.codepi/memories/` with hotness scoring (frequency + recency decay)
4. **Injects** relevant memories into the system prompt at the start of each new session

Memories are ranked by a blended score of topic relevance (80%) and hotness (20%), capped at a configurable token budget.

### Memory Categories

| Category | Examples |
|----------|----------|
| `decisions` | "Using SQLite over JSON for storage", "Switching to async handlers" |
| `patterns` | "Always check permissions before tool execution", "Error handling wraps all tool calls" |
| `file-knowledge` | "Auth logic is in core/security.py", "Config lives in config.toml" |
| `preferences` | "Prefer pytest over unittest", "Always use type hints" |

### Memory Config

```toml
[memory]
enabled = true                # Set to false to disable entirely
max_items = 500               # Max stored memories (LRU eviction)
injection_token_budget = 1000 # Max tokens injected into prompt
hotness_half_life_days = 7    # Hotness decay rate
dedup_jaccard_threshold = 0.7 # Similarity threshold for merge
```

## Plan Mode

Structured 5-phase planning workflow for complex tasks:

```bash
codepi --plan
```

Phases:
1. **UNDERSTAND** — Explore codebase, ask clarifying questions
2. **DESIGN** — Create implementation plan
3. **REVIEW** — User reviews and approves
4. **FINALIZE** — Write plan to `.codepi/plans/`
5. **EXIT** — Return to normal mode

During planning, file edits are blocked. Only the plan file can be written in FINALIZE phase.

Keyboard: `Ctrl+P` toggles plan mode during session.

## Auto Mode

Continuous autonomous execution for routine tasks:

```bash
codepi --auto
```

Features:
- **Iteration limit**: Pauses after N turns (default: 100)
- **Approval gates**: Prompts before push, PR, publish operations
- **Safety rules**: Still enforces security restrictions

Keyboard: `Ctrl+A` toggles auto mode during session.

### Auto Mode Config

```toml
[modes.auto]
enabled = false
max_iterations = 100
require_approval_for = ["push", "pr", "publish"]
pause_on_errors = true
```

## Security Monitor

Built-in security rules protect against dangerous operations:

| Category | Examples | Action |
|----------|----------|--------|
| Destructive | `rm -rf`, `DROP TABLE` | BLOCK |
| Hard-to-reverse | `git push --force`, `git reset --hard` | BLOCK |
| Shared state | `git push`, `gh pr create` | ASK |
| Credentials | `.env` files, API keys in code | ASK |

Configure in `config.toml`:

```toml
[security]
enabled = true
# rule_overrides = { "shared:push" = "allow" }
```

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run integration tests (requires API key)
OPENAI_API_KEY=... pytest tests/integration/

# Lint
# (add your linter here)
```

## Architecture

```
CLI → Modes → AgentSession → LLMProvider
                        ↓
                  ToolRegistry
                        ↓
                   Extensions
```

- **ai/**: LLM provider abstraction (OpenAI-compatible by default)
- **core/**: AgentSession (turn loop), SessionManager (persistence), memory system
- **tools/**: Built-in tools (read, write, edit, bash, find, grep, ls)
- **extensions/**: Python extension loader, skill loader, memory extension
- **tui/**: Terminal UI (prompt_toolkit + rich)
- **modes/**: interactive, print, RPC, SDK

## License

MIT
