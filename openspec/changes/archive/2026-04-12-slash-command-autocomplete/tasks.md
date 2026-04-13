## 1. Command Registry

- [x] 1.1 Create `codepi/core/commands.py` with `Command` dataclass (name, description, aliases, category) and `CommandRegistry` class with `register()`, `get()`, `list_commands()`, and `find_by_prefix()` methods
- [x] 1.2 Add `load_from_skill_loader(skill_loader)` method to `CommandRegistry` that scans skills with `opsx-` prefix and registers them as `/opsx:<name>` commands
- [x] 1.3 Add unit tests for `CommandRegistry`: register, duplicate overwrite, prefix search, skill loading, alias resolution

## 2. Slash Command Completer

- [x] 2.1 Create `SlashCommandCompleter` class in `codepi/core/commands.py` extending `prompt_toolkit.completion.Completer` that yields `Completion` objects for commands matching the current word prefix
- [x] 2.2 Ensure completer only triggers when the cursor is at the start of input and the first character is `/` (return empty for non-slash input or slash not at position 0)
- [x] 2.3 Add display metadata to completions: show command name as the completion text and description in the right column
- [x] 2.4 Add unit tests for `SlashCommandCompleter`: prefix filtering, no-match case, non-slash input ignored

## 3. RichInput Refactor

- [x] 3.1 Refactor `RichInput.__init__` to accept an optional `command_registry: CommandRegistry` parameter and create an internal `prompt_toolkit.PromptSession` with `SlashCommandCompleter` and `complete_while_typing=True`
- [x] 3.2 Replace `console.input()` in `_get_input_sync` with `self._prompt_session.prompt()` when a command_registry is provided, falling back to `console.input()` when not provided (backward compatibility)
- [x] 3.3 Preserve the `get_user_input()` async public API — no changes to callers
- [x] 3.4 Add tests for `RichInput`: verify completer is wired when registry is provided, verify fallback when registry is None

## 4. Integration

- [x] 4.1 In `InteractiveMode.__init__`, create a `CommandRegistry`, call `load_from_skill_loader(self._skill_loader)`, and pass it to `RichInput(command_registry=...)`
- [x] 4.2 Register any built-in slash commands in the registry (e.g., `/help`, `/clear`, `/model`, `/exit` if applicable — map to existing behaviors)
- [x] 4.3 Verify that existing `/opsx:` command handling in `AgentSession.prompt()` still works unchanged after the refactor
- [ ] 4.4 Manual smoke test: run `codepi`, type `/`, verify dropdown appears, type `/op`, verify filtered list, select a completion, verify it inserts correctly
