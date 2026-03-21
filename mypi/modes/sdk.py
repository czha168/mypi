from __future__ import annotations
import asyncio
from collections.abc import AsyncIterator
from mypi.core.agent_session import AgentSession
from mypi.core.session_manager import SessionManager
from mypi.ai.provider import LLMProvider
from mypi.tools.base import ToolRegistry
from mypi.extensions.skill_loader import SkillLoader


class SDK:
    def __init__(
        self,
        provider: LLMProvider,
        session_manager: SessionManager,
        model: str,
        tool_registry: ToolRegistry | None = None,
        extensions: list | None = None,
        system_prompt: str | None = None,
        skill_loader: SkillLoader | None = None,
    ):
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
        self._session = AgentSession(**kwargs)

    async def prompt(self, text: str) -> str:
        """Send a prompt and return the full assistant response as a string."""
        parts: list[str] = []
        self._session.on_token = lambda t: parts.append(t)
        await self._session.prompt(text)
        return "".join(parts)

    async def stream(self, text: str) -> AsyncIterator[str]:
        """Send a prompt and yield streaming tokens."""
        queue: asyncio.Queue[str | None] = asyncio.Queue()
        self._session.on_token = lambda t: queue.put_nowait(t)

        async def _run():
            await self._session.prompt(text)
            queue.put_nowait(None)  # sentinel

        task = asyncio.create_task(_run())
        while True:
            token = await queue.get()
            if token is None:
                break
            yield token
        await task
