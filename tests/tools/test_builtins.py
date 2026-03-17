import pytest
from pathlib import Path
from mypi.tools.builtins import ReadTool, WriteTool, EditTool, BashTool, FindTool, GrepTool, LsTool
from mypi.tools.base import ToolResult


@pytest.mark.asyncio
async def test_read_tool_reads_file(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("line1\nline2\nline3\n")
    tool = ReadTool()
    result = await tool.execute(path=str(f))
    assert "line1" in result.output
    assert "line2" in result.output


@pytest.mark.asyncio
async def test_read_tool_with_offset_and_limit(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("a\nb\nc\nd\ne\n")
    tool = ReadTool()
    result = await tool.execute(path=str(f), offset=2, limit=2)
    lines = result.output.strip().split("\n")
    assert len(lines) == 2
    assert "b" in result.output
    assert "a" not in result.output


@pytest.mark.asyncio
async def test_read_tool_missing_file():
    tool = ReadTool()
    result = await tool.execute(path="/nonexistent/file.py")
    assert result.error is not None


@pytest.mark.asyncio
async def test_write_tool_creates_file(tmp_path):
    f = tmp_path / "new.txt"
    tool = WriteTool()
    result = await tool.execute(path=str(f), content="hello world")
    assert result.error is None
    assert f.read_text() == "hello world"


@pytest.mark.asyncio
async def test_edit_tool_replaces_string(tmp_path):
    f = tmp_path / "edit.py"
    f.write_text("def foo():\n    return 1\n")
    tool = EditTool()
    result = await tool.execute(path=str(f), old_string="return 1", new_string="return 42")
    assert result.error is None
    assert "return 42" in f.read_text()


@pytest.mark.asyncio
async def test_edit_tool_fails_if_not_unique(tmp_path):
    f = tmp_path / "dupe.py"
    f.write_text("x = 1\nx = 1\n")
    tool = EditTool()
    result = await tool.execute(path=str(f), old_string="x = 1", new_string="x = 2")
    assert result.error is not None
    assert "not unique" in result.error


@pytest.mark.asyncio
async def test_edit_tool_fails_if_not_found(tmp_path):
    f = tmp_path / "notfound.py"
    f.write_text("x = 1\n")
    tool = EditTool()
    result = await tool.execute(path=str(f), old_string="y = 99", new_string="y = 0")
    assert result.error is not None


@pytest.mark.asyncio
async def test_bash_tool_runs_command():
    tool = BashTool()
    result = await tool.execute(command="echo hello")
    assert "hello" in result.output
    assert result.error is None


@pytest.mark.asyncio
async def test_bash_tool_captures_stderr():
    tool = BashTool()
    result = await tool.execute(command="echo err >&2; exit 1")
    assert result.error is not None or "err" in result.output


@pytest.mark.asyncio
async def test_bash_tool_timeout(tmp_path):
    tool = BashTool()
    result = await tool.execute(command="sleep 10", timeout=1)
    assert result.error is not None
    assert "timeout" in result.error.lower()


@pytest.mark.asyncio
async def test_find_tool_finds_files(tmp_path):
    (tmp_path / "a.py").write_text("x")
    (tmp_path / "b.txt").write_text("y")
    tool = FindTool()
    result = await tool.execute(path=str(tmp_path), pattern="*.py")
    assert "a.py" in result.output
    assert "b.txt" not in result.output


@pytest.mark.asyncio
async def test_grep_tool_finds_pattern(tmp_path):
    (tmp_path / "source.py").write_text("def hello():\n    return 42\n")
    tool = GrepTool()
    result = await tool.execute(pattern="def hello", path=str(tmp_path))
    assert "source.py" in result.output


@pytest.mark.asyncio
async def test_ls_tool_lists_directory(tmp_path):
    (tmp_path / "foo.txt").write_text("hi")
    (tmp_path / "bar.py").write_text("x")
    tool = LsTool()
    result = await tool.execute(path=str(tmp_path))
    assert "foo.txt" in result.output
    assert "bar.py" in result.output
