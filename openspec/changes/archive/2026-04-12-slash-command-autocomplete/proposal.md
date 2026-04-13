## Why

Users currently have no way to discover available slash commands without reading documentation. When a user types `/` in the interactive prompt, nothing happens — no suggestions, no feedback. This creates friction for discovering the `/opsx:` command family and any future slash commands. Adding auto-completion at the `/` trigger point would make commands discoverable, reduce typing, and provide a better interactive experience.

## What Changes

- Add a command registry that defines all slash commands (name, description, aliases, arguments) in a centralized data structure
- Replace the current `RichInput` (which uses `console.input()`) with `prompt_toolkit`-based input that supports completion
- When user types `/`, show a filtered dropdown of matching commands with descriptions
- Typing after `/` filters the list in real-time (e.g., `/op` shows `/opsx:apply`, `/opsx:explore`, etc.)
- Selecting a completion inserts the command text into the input buffer
- Integrate with the existing `SkillLoader` to dynamically include skill-based commands (e.g., `/opsx:*` from loaded skills)

## Capabilities

### New Capabilities
- `slash-command-completion`: Auto-completion dropdown triggered by `/` in the interactive prompt, showing available commands with descriptions, filtered by typed prefix, and powered by a centralized command registry

### Modified Capabilities

## Impact

- **codepi/tui/rich_components.py**: `RichInput` class needs to switch from `console.input()` to `prompt_toolkit` with a custom completer
- **codepi/modes/interactive.py**: `InteractiveMode` needs to pass the command registry to the input handler
- **New file**: Command registry module (likely `codepi/core/commands.py`) defining slash command metadata
- **Dependency**: Already using `prompt_toolkit` in `TUIApp`; the same library will be used for completion
- **No breaking changes**: Existing `/opsx:` handling in `agent_session.py` remains unchanged
