"""Command registry and slash command auto-completion for codepi."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from prompt_toolkit.completion import Completer, Completion

if TYPE_CHECKING:
    from codepi.extensions.skill_loader import SkillLoader


@dataclass
class Command:
    """Represents a slash command with metadata."""

    name: str
    description: str = ""
    aliases: list[str] = field(default_factory=list)
    category: str = "general"


class CommandRegistry:
    """Central registry for slash commands."""

    def __init__(self) -> None:
        self._commands: dict[str, Command] = {}

    def register(self, cmd: Command) -> None:
        """Register a command and its aliases. Duplicates overwrite silently."""
        self._commands[cmd.name] = cmd
        for alias in cmd.aliases:
            self._commands[alias] = cmd

    def get(self, name: str) -> Command | None:
        """Look up a command by name or alias."""
        return self._commands.get(name)

    def list_commands(self) -> list[Command]:
        """Return all unique commands, sorted by name."""
        seen_ids: set[int] = set()
        result: list[Command] = []
        for cmd in self._commands.values():
            if id(cmd) not in seen_ids:
                seen_ids.add(id(cmd))
                result.append(cmd)
        return sorted(result, key=lambda c: c.name)

    def find_by_prefix(self, prefix: str) -> list[Command]:
        """Return commands whose name starts with prefix, sorted alphabetically."""
        seen_ids: set[int] = set()
        result: list[Command] = []
        for name, cmd in self._commands.items():
            if name.startswith(prefix) and id(cmd) not in seen_ids:
                seen_ids.add(id(cmd))
                result.append(cmd)
        return sorted(result, key=lambda c: c.name)

    def load_from_skill_loader(self, skill_loader: SkillLoader) -> None:
        """Scan skills with opsx- prefix and register them as /opsx: commands."""
        skills = skill_loader.load_skills_metadata()
        opsx_prefix = "opsx-"
        for skill in skills:
            if skill.name.startswith(opsx_prefix):
                command_name = skill.name[len(opsx_prefix):]
                self.register(Command(
                    name=f"/opsx:{command_name}",
                    description=skill.description,
                    category="skills",
                ))


class SlashCommandCompleter(Completer):
    """Auto-completer for slash commands, triggered by / at the start of input."""

    def __init__(self, registry: CommandRegistry) -> None:
        self._registry = registry

    def get_completions(self, document, complete_event):
        """Yield completions for commands matching the current prefix."""
        text = document.text_before_cursor
        if not text.startswith("/"):
            return
        for cmd in self._registry.find_by_prefix(text):
            yield Completion(
                cmd.name,
                start_position=-len(text),
                display=cmd.name,
                display_meta=cmd.description,
            )
