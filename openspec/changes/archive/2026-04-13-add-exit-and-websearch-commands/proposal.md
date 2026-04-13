## Why

The interactive mode registers slash commands in `CommandRegistry` (including `/exit`, `/help`, `/clear`, `/model`) but has **no dispatch mechanism** — all input goes straight to `AgentSession.prompt()`, so typing `/exit` or `/clear` sends the slash command to the LLM as a regular message instead of handling it locally. Users need `/exit` to quit and `/websearch` to run web searches directly from the prompt without asking the LLM to invoke the tool.

## What Changes

- Add a command dispatch layer in `InteractiveMode` that intercepts slash commands before they reach `AgentSession.prompt()`
- Implement `/exit` handler: sets `_is_running = False` to break the main loop
- Implement `/websearch <query>` handler: calls `WebSearchTool.execute()` directly and renders results via `RichRenderer`
- Register `/websearch` in the builtin command list alongside existing commands
- Ensure `/help` displays all registered commands including `/websearch`

## Capabilities

### New Capabilities
- `slash-command-dispatch`: Local execution of slash commands in interactive mode — intercepts input starting with `/`, dispatches to registered handlers, and prevents the text from being sent to the LLM

### Modified Capabilities
- `slash-command-completion`: Add `/websearch` to the builtin command registration list so it appears in auto-completion

## Impact

- **Files changed**: `codepi/modes/interactive.py` (dispatch logic + handlers), `codepi/core/commands.py` (no changes needed — registry already supports this)
- **Dependencies**: `ddgs` (optional, already a dependency for `web_search` tool)
- **No breaking changes**: Commands not in the registry continue to pass through to `AgentSession` as before (e.g., `/opsx:*` commands)
