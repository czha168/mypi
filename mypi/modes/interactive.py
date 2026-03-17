from __future__ import annotations
from mypi.core.agent_session import AgentSession
from mypi.core.session_manager import SessionManager
from mypi.ai.provider import LLMProvider
from mypi.tools.base import ToolRegistry
from mypi.tui.app import TUIApp
from mypi.extensions.base import Extension


class InteractiveMode:
    def __init__(
        self,
        provider: LLMProvider,
        session_manager: SessionManager,
        model: str,
        session_id: str,
        tool_registry: ToolRegistry | None = None,
        extensions: list[Extension] | None = None,
        system_prompt: str | None = None,
    ):
        self._session_manager = session_manager
        self._app = TUIApp(
            model=model,
            session_id=session_id,
            on_cancel=lambda: None,  # handled by KeyboardInterrupt
            on_clear=lambda: None,
            on_checkpoint=lambda: None,
        )
        self._follow_up_queue: list[str] = []
        self._is_running = True

        kwargs: dict = dict(
            provider=provider,
            session_manager=session_manager,
            model=model,
            tool_registry=tool_registry,
            extensions=extensions or [],
        )
        if system_prompt:
            kwargs["system_prompt"] = system_prompt
        self._session = AgentSession(**kwargs)
        self._session.on_token = lambda t: self._app.renderer.append_token(t)
        self._session.on_tool_call = lambda n, a: self._app.renderer.render_tool_call(n, a)
        self._session.on_tool_result = lambda n, r: self._app.renderer.render_tool_result(n, r.output)
        self._session.on_error = lambda m: self._app.renderer.render_error(m)

    async def run(self) -> None:
        self._app.renderer.render_info(f"mypi — model: {self._app.model}  Ctrl+C to exit")
        while self._is_running:
            try:
                text = await self._app.get_input()
            except (EOFError, KeyboardInterrupt):
                break
            if not text.strip():
                continue
            self._app.renderer.render_user_message(text)
            self._app.renderer.start_turn()  # Reset buffer for new turn
            await self._session.prompt(text)
            self._app.renderer.end_turn()

            for queued in self._follow_up_queue:
                await self._session.follow_up(queued)
            self._follow_up_queue.clear()
