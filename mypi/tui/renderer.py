from __future__ import annotations
from rich.console import Console


class StreamingRenderer:
    """Renders streaming LLM output to the terminal using rich."""

    def __init__(self, console: Console | None = None):
        self.console = console or Console()
        self._buffer = ""

    def start_turn(self) -> None:
        """Called at the start of an assistant turn."""
        self._buffer = ""

    def append_token(self, token: str) -> None:
        """Append a streaming token and render inline."""
        self._buffer += token
        self.console.print(token, end="", highlight=False)

    def end_turn(self) -> None:
        """Called at the end of an assistant turn."""
        pass  # streaming already printed tokens inline

    def render_tool_call(self, name: str, args: dict) -> None:
        self.console.print(f"\n[bold cyan]● {name}[/bold cyan] {args}")

    def render_tool_result(self, name: str, content: str) -> None:
        preview = content[:300] + ("..." if len(content) > 300 else "")
        self.console.print(f"  [dim]└─ {preview}[/dim]")

    def render_user_message(self, text: str) -> None:
        self.console.print(f"\n[bold green]You:[/bold green] {text}")

    def render_error(self, message: str) -> None:
        self.console.print(f"\n[bold red]Error:[/bold red] {message}")

    def render_info(self, message: str) -> None:
        self.console.print(f"[dim]{message}[/dim]")
