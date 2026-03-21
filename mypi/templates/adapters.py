from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class CommandContent:
    id: str
    name: str
    description: str
    category: str
    tags: list[str]
    body: str


class ToolAdapter(ABC):
    tool_id: str

    @abstractmethod
    def get_file_path(self, command_id: str) -> str: ...

    @abstractmethod
    def format_file(self, content: CommandContent) -> str: ...


class ClaudeAdapter(ToolAdapter):
    tool_id = "claude"

    def get_file_path(self, command_id: str) -> str:
        return f".claude/commands/{command_id}.md"

    def format_file(self, content: CommandContent) -> str:
        return f"# {content.name}\n\n{content.body}"


class CursorAdapter(ToolAdapter):
    tool_id = "cursor"

    def get_file_path(self, command_id: str) -> str:
        return f".cursor/rules/{command_id}.md"

    def format_file(self, content: CommandContent) -> str:
        return f"---\nname: {content.name}\ndescription: {content.description}\ntags: {', '.join(content.tags)}\n---\n\n{content.body}"


class WindsurfAdapter(ToolAdapter):
    tool_id = "windsurf"

    def get_file_path(self, command_id: str) -> str:
        return f".windsurfrules/{command_id}"

    def format_file(self, content: CommandContent) -> str:
        return f"{content.name}\n\n{content.description}\n\n---\n\n{content.body}"


ADAPTERS: dict[str, ToolAdapter] = {
    "claude": ClaudeAdapter(),
    "cursor": CursorAdapter(),
    "windsurf": WindsurfAdapter(),
}
