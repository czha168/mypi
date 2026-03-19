# mypi

A minimalist terminal-based coding assistant written in Python. Give it a task, it uses file system and shell tools to read, edit, and execute code on your behalf.

Inspired by [pi-coding-agent](https://github.com/badlogic/pi-mono/tree/main/packages/coding-agent).

## Features

- **7 built-in tools**: read, write, edit, bash, find, grep, ls
- **4 operation modes**: interactive TUI, print mode, RPC mode, Python SDK
- **Session persistence**: Tree-structured JSONL with branching and auto-compaction
- **Extensible**: Python extensions + Claude Code-compatible skills
- **Any LLM**: Works with any OpenAI-compatible endpoint (Ollama, Groq, LM Studio, etc.)

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
mypi
```

## Configuration

Create `~/.mypi/config.toml`:

```toml
[provider]
base_url = "https://api.openai.com/v1"
api_key  = ""
model    = "gpt-4o"

[session]
compaction_threshold = 0.80
max_retries = 3
```

**Environment variables** (override config):

```bash
export OPENAI_API_KEY=sk-...
export OPENAI_BASE_URL=http://localhost:11434/v1  # Ollama
mypi --model codellama
```

## Usage Modes

### Interactive Mode (default)

```bash
mypi
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
mypi --print "List Python files in src/"
mypi --print "Fix the bug in parser.py" 2>&1 | tee fix.log
```

### RPC Mode

Integrate into editors/IDEs via JSONL stdin/stdout:

```bash
mypi --rpc
```

```json
{"type": "prompt", "text": "What does main.py do?"}
{"type": "tool_call", "name": "read", "arguments": {"path": "main.py"}}
{"type": "tool_result", "name": "read", "content": "..."}
```

### Python SDK

Embed in your application:

```python
from mypi.modes.sdk import SDK
from mypi.ai.openai_compat import OpenAICompatProvider
from mypi.core.session_manager import SessionManager
from mypi.tools.builtins import make_builtin_registry

provider = OpenAICompatProvider(base_url="...", api_key="...")
sm = SessionManager("~/.mypi/sessions")
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

## Extensions

Drop `.py` files into `~/.mypi/extensions/`:

```python
from mypi.extensions.base import Extension
from mypi.core.events import BeforeAgentStartEvent

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

Place in `~/.mypi/skills/` or add directories with `--skills-dir`.

## Session Management

Sessions are stored as JSONL files in `~/.mypi/sessions/`. Resume with:

```bash
mypi --session 550e8400-e29b-41d4-a716-446655440000
```

**Auto-compaction** triggers at 80% context window usage — the model summarizes conversation history to free up tokens.

**Branching** allows exploring alternative approaches. The session tree preserves history for each branch.

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
- **core/**: AgentSession (turn loop), SessionManager (persistence)
- **tools/**: Built-in tools (read, write, edit, bash, find, grep, ls)
- **extensions/**: Python extension loader, skill loader
- **tui/**: Terminal UI (prompt_toolkit + rich)
- **modes/**: interactive, print, RPC, SDK

## License

MIT
