## Context

The interactive mode (`codepi/modes/interactive.py`) currently uses `RichInput` which wraps `console.input()` from Rich. This is a simple blocking input call with no completion support. The `TUIApp` class already uses `prompt_toolkit.PromptSession` with a bottom toolbar and key bindings, but `InteractiveMode` bypasses it in favor of `RichInput`.

The only slash command handling today is in `agent_session.py`: the `_is_opsx_command()` method detects `/opsx:` prefixed input and routes it through `SkillLoader`. There is no command registry, no discovery mechanism, and no auto-completion.

The codebase already depends on `prompt_toolkit` (used in `TUIApp`) and `rich` (used for all rendering), so no new dependencies are needed.

## Goals / Non-Goals

**Goals:**
- Provide real-time command suggestions when user types `/` in the interactive prompt
- Support filtering as the user types more characters (e.g., `/op` → shows `/opsx:apply`, `/opsx:explore`)
- Dynamically include skill-based commands from `SkillLoader`
- Minimal disruption to existing code paths

**Non-Goals:**
- Argument-level completion (completing command arguments/parameters) — future enhancement
- Fuzzy matching — prefix-only filtering for simplicity
- Non-interactive modes (print, RPC, SDK) — these don't have a prompt loop
- Replacing the entire TUI with `prompt_toolkit` layout system — keep Rich for rendering

## Decisions

### D1: Use `prompt_toolkit.Completer` instead of custom Rich-based dropdown

**Choice**: Implement a `SlashCommandCompleter` extending `prompt_toolkit.completion.Completer`.

**Rationale**: `prompt_toolkit` has built-in completion UI (dropdown menu, multi-column display, filtering). The project already depends on it. Building a custom dropdown from scratch with Rich would be significantly more code and harder to maintain. `prompt_toolkit`'s completer integrates naturally with `PromptSession`.

**Alternatives considered**:
- Rich-based overlay panel: Would require manually managing cursor position, clearing/redrawing, and handling terminal escape codes. Fragile across terminals.
- Custom readline completer: Less feature-rich than `prompt_toolkit`, no built-in UI.

### D2: Replace `RichInput` with `prompt_toolkit.PromptSession` as the primary input mechanism

**Choice**: Refactor `RichInput` to internally use `prompt_toolkit.PromptSession` with the completer attached, instead of `console.input()`.

**Rationale**: `console.input()` from Rich is a thin wrapper over Python's `input()` — it has no completion support. Since the project already uses `prompt_toolkit` in `TUIApp`, consolidating on `prompt_toolkit` for input avoids maintaining two input systems. The Rich prompt styling can be replicated via `prompt_toolkit`'s formatted text.

**Alternatives considered**:
- Keep `console.input()` and add completion as a separate overlay: Requires intercepting keystrokes manually, re-rendering suggestions with Rich, and managing the overlay lifecycle. Extremely fragile.
- Use both systems side-by-side: Adds complexity with no benefit.

### D3: Create a `CommandRegistry` class as the single source of truth for slash commands

**Choice**: New file `codepi/core/commands.py` with a `CommandRegistry` class that holds command definitions (name, description, aliases, category) and supports dynamic registration.

**Rationale**: Currently, commands are scattered — `/opsx:` is hardcoded in `agent_session.py`, mode toggles are in keybindings, and there's no central list. A registry provides a single source of truth for both the completer and future help command. It also allows extensions to register custom commands.

**Alternatives considered**:
- Hardcode command list in the completer: Works but makes it harder for extensions to add commands and violates the existing extensibility patterns.
- Use `SkillLoader` directly: Skills are not 1:1 with slash commands; skills inject into prompts while commands are UI-level constructs.

### D4: Wire `SkillLoader` into `CommandRegistry` for dynamic `/opsx:*` commands

**Choice**: `CommandRegistry.load_from_skill_loader()` method that scans loaded skills and registers `/opsx:<name>` commands.

**Rationale**: The `/opsx:` family of commands are derived from skills. Rather than hardcoding them, the registry dynamically discovers them from `SkillLoader`, keeping the existing on-demand loading pattern intact.

## Risks / Trade-offs

- **Risk**: `prompt_toolkit` completion dropdown may conflict with Rich's rendering if both write to the terminal simultaneously → **Mitigation**: Rich only renders outside the input loop (between prompts). During input, only `prompt_toolkit` controls the terminal. This is already the pattern in `TUIApp`.

- **Risk**: Performance impact of scanning skills on every completion → **Mitigation**: Cache the command list; refresh only when skills are reloaded. `SkillLoader.load_skills_metadata()` is already designed for lightweight metadata-only loading.

- **Trade-off**: `prompt_toolkit`'s completion UI is functional but not as visually rich as a custom Rich panel → Acceptable because the primary goal is discoverability, not visual polish. The dropdown is already familiar from shells and IDEs.

- **Trade-off**: `RichInput` API changes — callers that depend on `console.input()` behavior will need adjustment → **Mitigation**: Keep the `RichInput` public API identical (`get_user_input()` method). Internal implementation changes are encapsulated.
