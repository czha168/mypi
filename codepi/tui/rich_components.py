"""Reusable Rich UI components for codepi terminal interface."""

from __future__ import annotations

import asyncio
from xml.sax.saxutils import escape as xml_escape
from typing import TYPE_CHECKING

from rich.console import Console
from rich.table import Table
from rich.text import Text
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML

if TYPE_CHECKING:
    from codepi.core.commands import CommandRegistry


class RichInput:
    """Async input handler with rich formatting."""

    def __init__(
        self,
        console: Console | None = None,
        command_registry: CommandRegistry | None = None,
    ):
        self.console = console or Console()
        self._command_registry = command_registry
        if command_registry is not None:
            from codepi.core.commands import SlashCommandCompleter
            self._prompt_session = PromptSession(
                completer=SlashCommandCompleter(command_registry),
                complete_while_typing=True,
            )
        else:
            self._prompt_session = None

    async def get_user_input(self, prompt: str = "You") -> str:
        if self._prompt_session is not None:
            formatted = HTML(f'<style fg="cyan" bold="bold">{xml_escape(prompt)} › </style>')
            try:
                return await self._prompt_session.prompt_async(formatted)
            except EOFError:
                raise KeyboardInterrupt
            except KeyboardInterrupt:
                raise
        else:
            prompt_text = Text(f"{prompt} › ", style="bold cyan")
            return await asyncio.to_thread(self._get_input_sync, prompt_text)

    def _get_input_sync(self, prompt: Text) -> str:
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
