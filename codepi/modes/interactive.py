import asyncio
from __future__ import annotations
from rich.console import Console

from codepi.core.agent_session import AgentSession
from codepi.core.session_manager import SessionManager
from codepi.ai.provider import LLMProvider
from codepi.tools.base import ToolRegistry
from codepi.tui.app import TUIApp
from codepi.tui.rich_renderer import RichRenderer
from codepi.tui.rich_components import RichInput
from codepi.extensions.base import Extension
from codepi.extensions.skill_loader import SkillLoader


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
        skill_loader: SkillLoader | None = None,
    ):
        self._session_manager = session_manager
        self._console = Console()
        self._renderer = RichRenderer(console=self._console)
        self._input_handler = RichInput(console=self._console)
        
        # Keep TUIApp for compatibility
        self._app = TUIApp(
            model=model,
            session_id=session_id,
            on_cancel=lambda: None,
            on_clear=lambda: None,
            on_checkpoint=lambda: None,
        )
        # Override renderer with Rich version
        self._app.renderer = self._renderer
        
        self._follow_up_queue: list[str] = []
        self._is_running = True
        self._model = model
        self._session_id = session_id

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
        
        # Wire callbacks to Rich renderer
        self._session.on_token = lambda t: self._renderer.append_token(t)
        self._session.on_tool_call = lambda n, a: self._renderer.render_tool_call(n, a)
        self._session.on_tool_result = lambda n, r: self._renderer.render_tool_result(n, r.output)
        self._session.on_error = lambda m: self._renderer.render_error(m)

    async def run(self) -> None:
        """Run interactive mode with Rich UI."""
        # Display welcome banner
        self._renderer.render_welcome(self._model, self._session_id)
        
        # Check for recovery checkpoint on startup
        recovery_checkpoint = self._session_manager.get_last_recovery_checkpoint()
        if recovery_checkpoint:
            retry_after = recovery_checkpoint.data.get("retry_after", 60)
            reason = recovery_checkpoint.data.get("reason", "Unknown error")
            
            self._renderer.render_recovery_checkpoint(retry_after, reason)
            self._renderer.render_info(f"⏳ Waiting {retry_after}s before retrying...")
            
            # Show countdown
            for i in range(retry_after, 0, -1):
                self._renderer.console.print(f"   Resuming in {i}s...", end="\r")
                await asyncio.sleep(1)
            self._renderer.console.print("   Ready!              ")
        
        # Main interaction loop
        self._renderer.render_separator("Interactive Session")
        
        while self._is_running:
            try:
                # Get user input with rich formatting
                text = await self._input_handler.get_user_input()
            except (EOFError, KeyboardInterrupt):
                self._renderer.render_info("Session ended by user")
                break
            
            if not text.strip():
                continue
            
            # Display user message
            self._renderer.render_user_message(text)
            
            # Start new turn (clear buffer)
            self._renderer.start_turn()
            
            try:
                # Process prompt
                await self._session.prompt(text)
            except Exception as e:
                self._renderer.render_error(f"Error: {e}")
                raise
            
            # End turn (display accumulated response)
            self._renderer.end_turn()
            
            self._renderer.render_separator()
            
            # Process follow-up queue
            for queued in self._follow_up_queue:
                await self._session.follow_up(queued)
            self._follow_up_queue.clear()
        
        self._renderer.render_info("Goodbye!")
