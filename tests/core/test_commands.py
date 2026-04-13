import pytest
from pathlib import Path
from unittest.mock import MagicMock
from codepi.core.commands import Command, CommandRegistry, SlashCommandCompleter
from codepi.extensions.skill_loader import SkillLoader


def _make_skill(tmp_path: Path, name: str, description: str = "") -> Path:
    path = tmp_path / f"{name}.md"
    path.write_text(f"---\nname: {name}\ndescription: {description}\n---\nBody text.\n")
    return path


class TestCommandRegistry:
    def test_register_and_get(self):
        reg = CommandRegistry()
        cmd = Command(name="/help", description="Show help")
        reg.register(cmd)
        assert reg.get("/help") is cmd

    def test_get_unknown_returns_none(self):
        reg = CommandRegistry()
        assert reg.get("/nope") is None

    def test_register_with_aliases(self):
        reg = CommandRegistry()
        cmd = Command(name="/exit", description="Exit", aliases=["/quit"])
        reg.register(cmd)
        assert reg.get("/exit") is cmd
        assert reg.get("/quit") is cmd

    def test_duplicate_overwrites(self):
        reg = CommandRegistry()
        reg.register(Command(name="/help", description="First"))
        reg.register(Command(name="/help", description="Second"))
        result = reg.get("/help")
        assert result is not None
        assert result.description == "Second"

    def test_list_commands_deduplicated(self):
        reg = CommandRegistry()
        cmd = Command(name="/exit", aliases=["/quit"])
        reg.register(cmd)
        commands = reg.list_commands()
        assert len(commands) == 1
        assert commands[0].name == "/exit"

    def test_list_commands_sorted(self):
        reg = CommandRegistry()
        reg.register(Command(name="/zoo"))
        reg.register(Command(name="/alpha"))
        reg.register(Command(name="/mid"))
        names = [c.name for c in reg.list_commands()]
        assert names == ["/alpha", "/mid", "/zoo"]

    def test_find_by_prefix(self):
        reg = CommandRegistry()
        reg.register(Command(name="/opsx:explore", description="Explore"))
        reg.register(Command(name="/opsx:apply", description="Apply"))
        reg.register(Command(name="/help", description="Help"))
        results = reg.find_by_prefix("/opsx:")
        assert len(results) == 2
        names = [c.name for c in results]
        assert "/opsx:apply" in names
        assert "/opsx:explore" in names

    def test_find_by_prefix_no_match(self):
        reg = CommandRegistry()
        reg.register(Command(name="/help"))
        assert reg.find_by_prefix("/xyz") == []

    def test_find_by_prefix_deduplicates_aliases(self):
        reg = CommandRegistry()
        cmd = Command(name="/exit", aliases=["/quit"])
        reg.register(cmd)
        results = reg.find_by_prefix("/")
        assert len(results) == 1


class TestLoadFromSkillLoader:
    def test_loads_opsx_skills(self, tmp_skills_dir):
        _make_skill(tmp_skills_dir, "opsx-explore", "Explore mode")
        _make_skill(tmp_skills_dir, "opsx-apply", "Apply changes")
        loader = SkillLoader(skills_dirs=[tmp_skills_dir])

        reg = CommandRegistry()
        reg.load_from_skill_loader(loader)

        explore = reg.get("/opsx:explore")
        assert explore is not None
        assert explore.description == "Explore mode"
        apply_cmd = reg.get("/opsx:apply")
        assert apply_cmd is not None
        assert apply_cmd.category == "skills"

    def test_skips_non_opsx_skills(self, tmp_skills_dir):
        _make_skill(tmp_skills_dir, "my-custom-skill", "Custom")
        _make_skill(tmp_skills_dir, "opsx-explore", "Explore")
        loader = SkillLoader(skills_dirs=[tmp_skills_dir])

        reg = CommandRegistry()
        reg.load_from_skill_loader(loader)

        assert reg.get("/opsx:explore") is not None
        assert reg.list_commands()[0].name == "/opsx:explore"

    def test_opsx_archive_change_dash_preserved(self, tmp_skills_dir):
        _make_skill(tmp_skills_dir, "opsx-archive-change", "Archive a change")
        loader = SkillLoader(skills_dirs=[tmp_skills_dir])

        reg = CommandRegistry()
        reg.load_from_skill_loader(loader)

        assert reg.get("/opsx:archive-change") is not None


class TestSlashCommandCompleter:
    def test_completes_slash_prefix(self):
        from prompt_toolkit.document import Document
        from prompt_toolkit.completion import CompleteEvent

        reg = CommandRegistry()
        reg.register(Command(name="/help", description="Show help"))
        reg.register(Command(name="/exit", description="Exit"))
        completer = SlashCommandCompleter(reg)

        doc = Document("/", cursor_position=1)
        completions = list(completer.get_completions(doc, CompleteEvent()))
        names = [c.text for c in completions]
        assert "/help" in names
        assert "/exit" in names

    def test_filters_by_prefix(self):
        from prompt_toolkit.document import Document
        from prompt_toolkit.completion import CompleteEvent

        reg = CommandRegistry()
        reg.register(Command(name="/help", description="Show help"))
        reg.register(Command(name="/exit", description="Exit"))
        completer = SlashCommandCompleter(reg)

        doc = Document("/h", cursor_position=2)
        completions = list(completer.get_completions(doc, CompleteEvent()))
        assert len(completions) == 1
        assert completions[0].text == "/help"

    def test_no_match_returns_empty(self):
        from prompt_toolkit.document import Document
        from prompt_toolkit.completion import CompleteEvent

        reg = CommandRegistry()
        reg.register(Command(name="/help"))
        completer = SlashCommandCompleter(reg)

        doc = Document("/xyz", cursor_position=4)
        completions = list(completer.get_completions(doc, CompleteEvent()))
        assert completions == []

    def test_non_slash_input_returns_empty(self):
        from prompt_toolkit.document import Document
        from prompt_toolkit.completion import CompleteEvent

        reg = CommandRegistry()
        reg.register(Command(name="/help"))
        completer = SlashCommandCompleter(reg)

        doc = Document("help me fix this bug", cursor_position=19)
        completions = list(completer.get_completions(doc, CompleteEvent()))
        assert completions == []

    def test_completion_has_display_meta(self):
        from prompt_toolkit.document import Document
        from prompt_toolkit.completion import CompleteEvent

        reg = CommandRegistry()
        reg.register(Command(name="/help", description="Show help"))
        completer = SlashCommandCompleter(reg)

        doc = Document("/", cursor_position=1)
        completions = list(completer.get_completions(doc, CompleteEvent()))
        meta = completions[0].display_meta
        assert "Show help" in str(meta)

    def test_start_position_replaces_prefix(self):
        from prompt_toolkit.document import Document
        from prompt_toolkit.completion import CompleteEvent

        reg = CommandRegistry()
        reg.register(Command(name="/help", description="Show help"))
        completer = SlashCommandCompleter(reg)

        doc = Document("/h", cursor_position=2)
        completions = list(completer.get_completions(doc, CompleteEvent()))
        assert completions[0].start_position == -2
