from __future__ import annotations
import asyncio
import re
import shutil
from datetime import datetime
from pathlib import Path
from mypi.tools.base import Tool, ToolResult


class ReadTool(Tool):
    name = "read"
    description = "Read a file's contents. Optional offset (1-based line number to start from) and limit (max lines to return)."
    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Absolute or relative file path"},
            "offset": {"type": "integer", "description": "1-based line to start reading from"},
            "limit": {"type": "integer", "description": "Maximum number of lines to return"},
        },
        "required": ["path"],
    }

    async def execute(self, path: str, offset: int = 1, limit: int | None = None) -> ToolResult:
        try:
            lines = Path(path).read_text().splitlines()
            start = max(0, offset - 1)
            end = start + limit if limit is not None else len(lines)
            selected = lines[start:end]
            return ToolResult(output="\n".join(selected))
        except FileNotFoundError:
            return ToolResult(error=f"File not found: {path}")
        except Exception as e:
            return ToolResult(error=str(e))


class WriteTool(Tool):
    name = "write"
    description = "Write content to a file, creating or overwriting it."
    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "content": {"type": "string"},
        },
        "required": ["path", "content"],
    }

    async def execute(self, path: str, content: str) -> ToolResult:
        try:
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content)
            return ToolResult(output=f"Written {len(content)} characters to {path}")
        except Exception as e:
            return ToolResult(error=str(e))


class EditTool(Tool):
    name = "edit"
    description = "Replace old_string with new_string in a file. Fails if old_string appears 0 or 2+ times."
    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "old_string": {"type": "string"},
            "new_string": {"type": "string"},
        },
        "required": ["path", "old_string", "new_string"],
    }

    async def execute(self, path: str, old_string: str, new_string: str) -> ToolResult:
        try:
            content = Path(path).read_text()
            count = content.count(old_string)
            if count == 0:
                return ToolResult(error=f"old_string not found in {path}")
            if count > 1:
                return ToolResult(error=f"old_string is not unique in {path} ({count} occurrences)")
            new_content = content.replace(old_string, new_string, 1)
            Path(path).write_text(new_content)
            return ToolResult(output=f"Replaced 1 occurrence in {path}")
        except FileNotFoundError:
            return ToolResult(error=f"File not found: {path}")
        except Exception as e:
            return ToolResult(error=str(e))


class BashTool(Tool):
    name = "bash"
    description = "Execute a shell command. Returns stdout. Use timeout to prevent hanging."
    input_schema = {
        "type": "object",
        "properties": {
            "command": {"type": "string"},
            "timeout": {"type": "number", "description": "Seconds before killing the command (default 30)"},
        },
        "required": ["command"],
    }

    async def execute(self, command: str, timeout: float = 30) -> ToolResult:
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            try:
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()  # reap process and drain pipe
                return ToolResult(error=f"Command timeout after {timeout}s")
            output = stdout.decode(errors="replace")
            if proc.returncode != 0:
                return ToolResult(output=output, error=f"Exit code {proc.returncode}: {output.strip()[:200]}")
            return ToolResult(output=output)
        except Exception as e:
            return ToolResult(error=str(e))


class FindTool(Tool):
    name = "find"
    description = "Find files matching a glob pattern, sorted by modification time (newest first)."
    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Directory to search in"},
            "pattern": {"type": "string", "description": "Glob pattern, e.g. '*.py'"},
        },
        "required": ["path", "pattern"],
    }

    async def execute(self, path: str, pattern: str) -> ToolResult:
        try:
            matches = sorted(
                Path(path).rglob(pattern),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            return ToolResult(output="\n".join(str(m) for m in matches))
        except Exception as e:
            return ToolResult(error=str(e))


class GrepTool(Tool):
    name = "grep"
    description = "Search file contents for a regex pattern. Uses ripgrep if available, falls back to Python re."
    input_schema = {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Regex pattern"},
            "path": {"type": "string", "description": "Directory or file to search"},
            "glob": {"type": "string", "description": "File glob filter, e.g. '*.py'"},
        },
        "required": ["pattern", "path"],
    }

    async def execute(self, pattern: str, path: str, glob: str | None = None) -> ToolResult:
        if shutil.which("rg"):
            return await self._rg(pattern, path, glob)
        return await self._python_grep(pattern, path, glob)

    async def _rg(self, pattern: str, path: str, glob: str | None) -> ToolResult:
        cmd = ["rg", "--line-number", pattern, path]
        if glob:
            cmd += ["--glob", glob]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
            if proc.returncode not in (0, 1):
                return ToolResult(error=stderr.decode(errors="replace"))
            return ToolResult(output=stdout.decode(errors="replace"))
        except Exception as e:
            return ToolResult(error=str(e))

    async def _python_grep(self, pattern: str, path: str, glob: str | None) -> ToolResult:
        try:
            rx = re.compile(pattern)
            results = []
            search_path = Path(path)
            files = search_path.rglob(glob or "*") if search_path.is_dir() else [search_path]
            for f in files:
                if not f.is_file():
                    continue
                try:
                    for i, line in enumerate(f.read_text(errors="replace").splitlines(), 1):
                        if rx.search(line):
                            results.append(f"{f}:{i}: {line}")
                except Exception:
                    pass
            return ToolResult(output="\n".join(results))
        except re.error as e:
            return ToolResult(error=f"Invalid regex: {e}")


class LsTool(Tool):
    name = "ls"
    description = "List directory contents with file metadata. Use '.' for current directory."
    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Directory to list (use '.' for current directory)"},
        },
        "required": ["path"],
    }

    async def execute(self, path: str) -> ToolResult:
        try:
            entries = []
            for p in sorted(Path(path).iterdir()):
                stat = p.stat()
                kind = "dir" if p.is_dir() else "file"
                size = stat.st_size
                mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
                entries.append(f"{kind:4}  {size:>8}  {mtime}  {p.name}")
            return ToolResult(output="\n".join(entries))
        except Exception as e:
            return ToolResult(error=str(e))


def make_builtin_registry() -> "ToolRegistry":
    """Create a ToolRegistry pre-populated with all 7 built-in tools."""
    from mypi.tools.base import ToolRegistry
    reg = ToolRegistry()
    for tool in [ReadTool(), WriteTool(), EditTool(), BashTool(), FindTool(), GrepTool(), LsTool()]:
        reg.register(tool)
    return reg
