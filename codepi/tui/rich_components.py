"""Reusable Rich UI components for codepi terminal interface."""

from rich.console import Console
from rich.table import Table
from rich.text import Text
from typing import Optional
import asyncio


class RichInput:
    """Async input handler with rich formatting."""
    
    def __init__(self, console: Console | None = None):
        self.console = console or Console()
    
    async def get_user_input(self, prompt: str = "You") -> str:
        """Get user input with rich prompt."""
        prompt_text = Text(f"{prompt} › ", style="bold cyan")
        return await asyncio.to_thread(self._get_input_sync, prompt_text)
    
    def _get_input_sync(self, prompt: Text) -> str:
        """Synchronous input with rich prompt."""
        try:
            return self.console.input(prompt)
        except EOFError:
            raise KeyboardInterrupt
        except KeyboardInterrupt:
            raise


class RichTable:
    """Utility for creating formatted tables."""
    
    @staticmethod
    def create_two_column(title: str, rows: list[tuple[str, str]]) -> Table:
        """Create a two-column formatted table."""
        table = Table(title=title, show_header=False, expand=False)
        for key, value in rows:
            table.add_row(
                Text(key, style="bold cyan"),
                Text(value, style="white"),
            )
        return table
    
    @staticmethod
    def create_tool_table(tool_name: str, args: dict) -> Table:
        """Create a formatted table for tool arguments."""
        table = Table(
            title=f"🔧 {tool_name}",
            show_header=True,
            expand=False,
        )
        table.add_column("Param", style="cyan")
        table.add_column("Value", style="yellow")
        
        for key, val in args.items():
            table.add_row(key, str(val)[:50])
        
        return table
