"""Rich-based terminal UI renderer for beautiful, interactive output."""

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.align import Align
from rich.rule import Rule
import json
from datetime import datetime


class RichRenderer:
    """High-level terminal UI renderer using Rich library."""
    
    def __init__(self, console: Console | None = None):
        self.console = console or Console()
        self._buffer = ""
    
    # ========================================================================
    # Core Display Methods
    # ========================================================================
    
    def render_welcome(self, model: str, session_id: str) -> None:
        """Display welcome banner with session info."""
        title_text = Text("codepi", style="bold cyan")
        title_text.append(" — AI Coding Agent", style="white")
        
        info = Table.grid(padding=(0, 2))
        info.add_row("Model:", Text(model, style="green"))
        info.add_row("Session:", Text(session_id[:8] + "…", style="dim blue"))
        info.add_row("Status:", Text("Ready", style="bold green"))
        
        self.console.print(
            Panel(
                info,
                title=title_text,
                border_style="cyan",
                expand=False,
                padding=(1, 2),
            )
        )
        self.console.print(Align.center(Text("Ctrl+C to exit", style="dim white")))
        self.console.print()
    
    def render_user_message(self, text: str) -> None:
        """Display user message in a styled box."""
        panel = Panel(
            Text(text, style="white"),
            title=Text("You", style="bold blue"),
            border_style="blue",
            expand=True,
            padding=(0, 1),
        )
        self.console.print(panel)
    
    def append_token(self, token: str) -> None:
        """Stream individual tokens for assistant response."""
        self.console.print(token, end="", soft_wrap=True)
        self._buffer += token
    
    def start_turn(self) -> None:
        """Reset buffer for new turn."""
        self._buffer = ""
    
    def end_turn(self) -> None:
        """Render complete assistant message and clear buffer."""
        if self._buffer.strip():
            # Ensure Panel starts on a new line after streaming output
            self.console.print()
            panel = Panel(
                Markdown(self._buffer),
                title=Text("Assistant", style="bold green"),
                border_style="green",
                expand=True,
                padding=(0, 1),
            )
            self.console.print(panel)
        self._buffer = ""
    
    # ========================================================================
    # Tool Call Display
    # ========================================================================
    
    def render_tool_call(self, tool_name: str, arguments: dict) -> None:
        """Display tool call with arguments in formatted table."""
        table = Table(title=f"🔧 Calling: {tool_name}", show_header=True)
        table.add_column("Parameter", style="cyan")
        table.add_column("Value", style="yellow")
        
        for key, value in arguments.items():
            if isinstance(value, (dict, list)):
                value_str = json.dumps(value, indent=2)[:100]
            else:
                value_str = str(value)[:100]
            table.add_row(key, value_str)
        
        self.console.print(table)
    
    def render_tool_result(self, tool_name: str, result: str) -> None:
        """Display tool execution result."""
        display_result = result[:500] + "…" if len(result) > 500 else result
        
        panel = Panel(
            Text(display_result, style="white"),
            title=Text(f"✓ {tool_name} Result", style="bold green"),
            border_style="green",
            expand=True,
            padding=(0, 1),
        )
        self.console.print(panel)
    
    # ========================================================================
    # Error & Status Display
    # ========================================================================
    
    def render_error(self, message: str) -> None:
        """Display error message with red styling."""
        panel = Panel(
            Text(message, style="bold red"),
            title=Text("❌ Error", style="bold red"),
            border_style="red",
            expand=True,
            padding=(0, 1),
        )
        self.console.print(panel)
    
    def render_info(self, message: str) -> None:
        """Display informational message."""
        panel = Panel(
            Text(message, style="white"),
            title=Text("ℹ️  Info", style="bold cyan"),
            border_style="cyan",
            expand=True,
            padding=(0, 1),
        )
        self.console.print(panel)
    
    def render_warning(self, message: str) -> None:
        """Display warning message."""
        panel = Panel(
            Text(message, style="bold yellow"),
            title=Text("⚠️  Warning", style="bold yellow"),
            border_style="yellow",
            expand=True,
            padding=(0, 1),
        )
        self.console.print(panel)
    
    def render_success(self, message: str) -> None:
        """Display success message."""
        panel = Panel(
            Text(message, style="bold green"),
            title=Text("✓ Success", style="bold green"),
            border_style="green",
            expand=True,
            padding=(0, 1),
        )
        self.console.print(panel)
    
    # ========================================================================
    # Rate Limit & Recovery Display
    # ========================================================================
    
    def render_rate_limit(self, retry_after: int, reason: str) -> None:
        """Display rate limit message with retry countdown."""
        info = Table.grid(padding=(0, 2))
        info.add_row("Status:", Text("Rate Limited", style="bold yellow"))
        info.add_row("Reason:", Text(reason, style="yellow"))
        info.add_row("Retry in:", Text(f"{retry_after}s", style="bold cyan"))
        
        panel = Panel(
            info,
            title=Text("🔄 Rate Limit", style="bold yellow"),
            border_style="yellow",
            expand=True,
            padding=(1, 2),
        )
        self.console.print(panel)
    
    def render_recovery_checkpoint(self, retry_after: int, reason: str) -> None:
        """Display recovery checkpoint info on startup."""
        info = Table.grid(padding=(0, 2))
        info.add_row("Recovery Checkpoint Detected", style="bold yellow")
        info.add_row("Reason:", Text(reason, style="yellow"))
        info.add_row("Waiting:", Text(f"{retry_after}s", style="bold cyan"))
        
        panel = Panel(
            info,
            title=Text("♻️  Recovering", style="bold yellow"),
            border_style="yellow",
            expand=True,
            padding=(1, 2),
        )
        self.console.print(panel)
    
    # ========================================================================
    # Code Display
    # ========================================================================
    
    def render_code(self, code: str, language: str = "python", title: str = "Code") -> None:
        """Display formatted code snippet."""
        syntax = Syntax(code, language, theme="monokai", line_numbers=True)
        panel = Panel(
            syntax,
            title=Text(title, style="bold cyan"),
            border_style="cyan",
            expand=True,
        )
        self.console.print(panel)
    
    # ========================================================================
    # Separator
    # ========================================================================
    
    def render_separator(self, title: str = "") -> None:
        """Display horizontal separator."""
        if title:
            self.console.print(Rule(title=title, style="dim blue"))
        else:
            self.console.print(Rule(style="dim blue"))
