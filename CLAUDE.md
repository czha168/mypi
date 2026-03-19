# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

This project is to implment a minimalist terminal-based coding assistant in Python with referece to `pi-coding-agent` architecture which is analyzed in the document `pi-coding-agent.md`.

## pi-coding-agent Architecture Overview

The actual source lives in a monorepo located at [coding agent repository](https://github.com/badlogic/pi-mono/tree/main/packages/coding-agent). Key architectural facts from the documentation:

### Core Packages
- `@mariozechner/pi-agent-core` — [agent runtime primitives](https://github.com/badlogic/pi-mono/tree/main/packages/agent)
- `@mariozechner/pi-ai` — [LLM provider abstraction](https://github.com/badlogic/pi-mono/tree/main/packages/ai)
- `@mariozechner/pi-tui` — [terminal UI components](https://github.com/badlogic/pi-mono/tree/main/packages/tui)

### Key Source Files (in the monorepo)
- `packages/coding-agent/src/core/agent-session.ts` (~3,000 lines) — LLM conversation management, retry/compaction logic, extension binding
- `packages/coding-agent/src/core/session-manager.ts` — JSONL tree-structured session persistence with version migration (v1→v2→v3)
- `packages/coding-agent/src/core/extensions/index.ts` + `types.ts` — extension hook framework
- `packages/coding-agent/src/core/tools/index.ts` — 7 built-in tools: `read`, `write`, `edit`, `bash`, `find`, `grep`, `ls`
- `packages/coding-agent/src/modes/interactive/interactive-mode.ts` (~4,400 lines) — TUI with component system

### Four Operation Modes
| Mode | Entry Point | Use Case |
|------|-------------|----------|
| Interactive | `InteractiveMode` | Terminal UI sessions |
| Print | `PrintMode` | Scripting/automation |
| RPC | `RPCMode` | JSONL inter-process protocol |
| SDK | `SDK` | Embedding in applications |

### Extension System
Extensions hook into the agent lifecycle via:
- `BeforeAgentStartEvent` — modify system prompt
- `BeforeProviderRequestEvent` — modify LLM request params
- `ToolCallEvent` / `ToolResultEvent` — intercept tool execution
- `SessionForkEvent` / `SessionTreeEvent` — session branching hooks

Extensions can also register custom tools, keyboard shortcuts, and UI components (header/footer/widgets) with hot-reload support.

### Session Storage
Sessions are stored as JSONL files with a tree structure (each entry has `id` + `parentId`). Branching creates new tree nodes in the same file, not new files. Context reconstruction traverses from leaf to root, skipping compacted entries while keeping their summaries.
