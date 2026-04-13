## Context

codepi's interactive mode (`InteractiveMode`) registers slash commands (`/help`, `/clear`, `/exit`, `/model`) in a `CommandRegistry` with auto-completion support via `SlashCommandCompleter`. However, the main loop in `InteractiveMode.run()` sends all user input directly to `AgentSession.prompt()`, which forwards it to the LLM. There is no intercept layer that handles slash commands locally.

The `WebSearchTool` already exists as an LLM-callable tool using DuckDuckGo (`ddgs`). The user wants `/websearch <query>` to execute searches directly from the prompt without LLM involvement.

The `RichRenderer` provides terminal output methods (`render_info`, `render_error`, `render_separator`, etc.) for displaying results.

## Goals / Non-Goals

**Goals:**
- Intercept slash command input in `InteractiveMode` before it reaches `AgentSession.prompt()`
- Execute `/exit` (and alias `/quit`) by setting `_is_running = False`
- Execute `/websearch <query>` by calling `WebSearchTool.execute()` directly and rendering results via `RichRenderer`
- Ensure unhandled slash commands (e.g., `/opsx:*`) still pass through to `AgentSession` as before
- `/help` displays all registered commands including the new `/websearch`

**Non-Goals:**
- Refactoring the command system into a separate handler class (keep it simple in `InteractiveMode`)
- Making `/websearch` configurable (hardcode DuckDuckGo backend)
- Adding pagination or interactive result browsing
- Supporting `/websearch` in non-interactive modes (print, RPC, SDK)

## Decisions

### Decision 1: Dispatch in InteractiveMode, not AgentSession

**Choice**: Add `_dispatch_command(text)` method to `InteractiveMode` that runs before `self._session.prompt(text)`.

**Rationale**: `AgentSession` is LLM-agnostic and handles the turn loop. Slash command dispatch is a UI-layer concern — only interactive mode needs it. Keeping it in `InteractiveMode` avoids polluting the session with TUI logic.

**Alternative**: Add a hook in `AgentSession.prompt()` to call a command handler callback. Rejected — adds coupling between session and UI for a feature only interactive mode needs.

### Decision 2: Instantiate WebSearchTool lazily in the handler

**Choice**: Create `WebSearchTool` instance on-demand inside the `/websearch` handler, catching `ImportError` for missing `ddgs`.

**Rationale**: Avoids a hard dependency at module level. The tool already handles missing `ddgs` gracefully with an error message.

**Alternative**: Register `WebSearchTool` as a persistent instance. Rejected — unnecessary state for a one-shot command invocation.

### Decision 3: Pass-through for unrecognized commands

**Choice**: If `_dispatch_command()` doesn't recognize the command, return `False` and let the caller fall through to `AgentSession.prompt()`.

**Rationale**: `/opsx:*` commands are handled by `AgentSession._handle_opsx_command()` and must continue working. Other unknown `/`-prefixed input should go to the LLM (user might be typing a literal slash).

### Decision 4: Command handler signature

**Choice**: Handler functions are `async def _handle_xxx(self, args: str) -> None` where `args` is everything after the command name (trimmed).

**Rationale**: Simple, consistent interface. `/websearch python asyncio` passes `"python asyncio"` as args. `/exit` passes `""`.

## Risks / Trade-offs

- **[Risk] `/websearch` without args does nothing useful** → Mitigation: Display a usage message if args are empty
- **[Risk] Search results are plain text, not rich** → Mitigation: Use `RichRenderer.render_info()` which supports markdown-like formatting; acceptable for v1
- **[Risk] Command handlers grow over time** → Mitigation: If more than 5-6 commands are added, refactor into a `CommandHandler` protocol class. For now, inline methods are simpler.
