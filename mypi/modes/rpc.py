from __future__ import annotations
import asyncio
import json
import sys
from mypi.core.agent_session import AgentSession
from mypi.core.session_manager import SessionManager
from mypi.ai.provider import LLMProvider
from mypi.tools.base import ToolRegistry


class RPCMode:
    def __init__(
        self,
        provider: LLMProvider,
        session_manager: SessionManager,
        model: str,
        tool_registry: ToolRegistry | None = None,
        extensions: list | None = None,
    ):
        self._session = AgentSession(
            provider=provider,
            session_manager=session_manager,
            model=model,
            tool_registry=tool_registry,
            extensions=extensions or [],
        )

        self._session.on_token = lambda t: self._emit({"type": "token", "text": t})
        self._session.on_tool_call = lambda n, a: self._emit({"type": "tool_call", "name": n, "arguments": a})
        self._session.on_tool_result = lambda n, r: self._emit({"type": "tool_result", "name": n, "content": r.output})
        self._session.on_error = lambda m: self._emit({"type": "error", "message": m})

    def _emit(self, obj: dict) -> None:
        # Write synchronously — callbacks fire inside async loop, must not yield
        sys.stdout.write(json.dumps(obj) + "\n")
        sys.stdout.flush()

    async def run(self, reader: asyncio.StreamReader | None = None) -> None:
        if reader is None:
            reader = asyncio.StreamReader()
            loop = asyncio.get_event_loop()
            loop.add_reader(sys.stdin.fileno(), lambda: reader.feed_data(sys.stdin.buffer.read1()))

        while True:
            try:
                line = await reader.readline()
            except Exception:
                break
            if not line:
                break
            text = line.decode().strip()
            if not text:
                continue
            try:
                cmd = json.loads(text)
            except json.JSONDecodeError:
                self._emit({"type": "error", "message": f"Invalid JSON: {text}"})
                continue

            cmd_type = cmd.get("type")
            if cmd_type == "prompt":
                await self._session.prompt(cmd.get("text", ""))
                self._emit({"type": "done", "usage": {}})
            elif cmd_type == "steer":
                await self._session.steer(cmd.get("text", ""))
                self._emit({"type": "done", "usage": {}})
            elif cmd_type == "follow_up":
                await self._session.follow_up(cmd.get("text", ""))
                self._emit({"type": "done", "usage": {}})
            elif cmd_type == "cancel":
                self._emit({"type": "cancelled"})
            elif cmd_type == "exit":
                break
            else:
                self._emit({"type": "error", "message": f"Unknown command: {cmd_type}"})
