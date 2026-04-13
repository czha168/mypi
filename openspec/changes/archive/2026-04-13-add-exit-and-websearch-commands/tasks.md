## 1. Command Dispatch Infrastructure

- [x] 1.1 Add `_dispatch_command(self, text: str) -> bool` method to `InteractiveMode` that checks if input starts with `/`, looks up the command in `self._command_registry`, and returns `True` if handled locally, `False` otherwise
- [x] 1.2 Wire `_dispatch_command()` into the main loop in `InteractiveMode.run()` — call it before `self._session.prompt(text)` and `continue` the loop if it returns `True`
- [x] 1.3 Parse command name and arguments: split input on first whitespace, strip the command name (e.g., `/websearch`), pass remainder as args string

## 2. Built-in Command Handlers

- [x] 2.1 Implement `_handle_exit(self, args: str) -> None` — set `self._is_running = False` to break the main loop
- [x] 2.2 Implement `_handle_help(self, args: str) -> None` — call `self._command_registry.list_commands()` and render a formatted table via `RichRenderer`
- [x] 2.3 Implement `_handle_websearch(self, args: str) -> None` — validate args non-empty (show usage if empty), instantiate `WebSearchTool`, call `execute(query=args)`, render output or error via `RichRenderer`
- [x] 2.4 Implement `_handle_clear(self, args: str) -> None` — clear the terminal via `self._console.clear()`
- [x] 2.5 Register handlers in a dispatch map: `_command_handlers: dict[str, Callable[[str], None]]` mapping command names to handler methods

## 3. Command Registration

- [x] 3.1 Add `/websearch` to the builtin commands list in `_register_builtin_commands()` with description "Search the web using DuckDuckGo" and category "general"
- [x] 3.2 Register `/help` handler in dispatch map (currently registered but not handled)

## 4. Testing

- [x] 4.1 Write unit tests for `_dispatch_command()` — verify it returns `True` for `/exit`, `/quit`, `/help`, `/websearch`, `/clear` and `False` for unknown commands and non-slash input
- [x] 4.2 Write unit test for `/exit` — verify `_is_running` is set to `False`
- [x] 4.3 Write unit test for `/websearch` with empty args — verify usage message is displayed
- [x] 4.4 Write unit test for `/websearch` with query — verify `WebSearchTool.execute()` is called and results are rendered
- [x] 4.5 Write unit test for `/help` — verify all registered commands appear in output
- [x] 4.6 Run end-to-end test with `python3 -m codepi` using config from `/Users/czha168/.codepi/config.z-ai.toml` to verify `/exit` and `/websearch` work in the actual terminal
