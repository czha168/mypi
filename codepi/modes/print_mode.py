from __future__ import annotations
import sys
from typing import IO
from codepi.core.agent_session import AgentSession
from codepi.core.session_manager import SessionManager
from codepi.ai.provider import LLMProvider
from codepi.tools.base import ToolRegistry
from codepi.extensions.skill_loader import SkillLoader


class PrintMode:
    def __init__(
        self,
        provider: LLMProvider,
        session_manager: SessionManager,
        model: str,
        tool_registry: ToolRegistry | None = None,
        extensions: list | None = None,
        system_prompt: str | None = None,
        output: IO[str] = sys.stdout,
        skill_loader: SkillLoader | None = None,
    ):
        self.output = output
        kwargs: dict = dict(
            provider=provider,
            session_manager=session_manager,
            model=model,
            tool_registry=tool_registry,
            extensions=extensions or [],
            skill_loader=skill_loader,
        )
        if system_prompt:
            kwargs["system_prompt"] = system_prompt
        self.session = AgentSession(**kwargs)
        self.session.on_token = lambda t: self._write(t)
        self.session.on_tool_call = lambda name, args: self._write(f"\n[tool: {name}] {args}\n")
        self.session.on_tool_result = lambda name, result: self._write(f"[result: {name}] {result.output[:200]}\n")
        self.session.on_error = lambda msg: self._write(f"\nError: {msg}\n")

    def _write(self, text: str) -> None:
        self.output.write(text)
        self.output.flush()

    async def run(self, prompt: str) -> None:
        await self.session.prompt(prompt)
        self._write("\n")
