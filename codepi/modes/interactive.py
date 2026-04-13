from __future__ import annotations
import asyncio
from typing import TYPE_CHECKING
from rich.console import Console
from pathlib import Path

from codepi.core.agent_session import AgentSession
from codepi.core.session_manager import SessionManager
from codepi.core.commands import CommandRegistry
from codepi.ai.provider import LLMProvider
from codepi.tools.base import ToolRegistry
from codepi.tui.app import TUIApp
from codepi.tui.rich_renderer import RichRenderer
from codepi.tui.rich_components import RichInput
from codepi.extensions.base import Extension
from codepi.extensions.skill_loader import SkillLoader

if TYPE_CHECKING:
    from codepi.core.security import SecurityMonitor
    from codepi.core.modes.plan_mode import PlanModeManager
    from codepi.core.modes.auto_mode import AutoModeManager


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
        security_monitor: "SecurityMonitor | None" = None,
        plan_mode_manager: "PlanModeManager | None" = None,
        auto_mode_manager: "AutoModeManager | None" = None,
    ):
        self._session_manager = session_manager
        self._console = Console()
        self._renderer = RichRenderer(console=self._console)

        self._command_registry = CommandRegistry()
        if skill_loader:
            self._command_registry.load_from_skill_loader(skill_loader)
        self._register_builtin_commands()

        self._input_handler = RichInput(
            console=self._console,
            command_registry=self._command_registry,
        )
        self._security_monitor = security_monitor
        self._plan_mode_manager = plan_mode_manager
        self._auto_mode_manager = auto_mode_manager
        self._current_mode = "normal"
        self._current_phase = None
        
        # Keep TUIApp for compatibility
        self._app = TUIApp(
            model=model,
            session_id=session_id,
            on_cancel=lambda: None,
            on_clear=lambda: None,
            on_checkpoint=lambda: None,
            get_mode_info=self._get_mode_info,
        )
        # Override renderer with Rich version
        self._app.renderer = self._renderer
        
        self._follow_up_queue: list[str] = []
        self._is_running = True
        self._model = model
        self._session_id = session_id

        ext_list = list(extensions or [])
        try:
            from codepi.config import load_config
            cfg = load_config()
            if cfg.memory.enabled:
                from codepi.extensions.memory_extension import MemoryExtension
                ext_list.append(MemoryExtension(config=cfg.memory))
        except Exception:
            pass

        kwargs: dict = dict(
            provider=provider,
            session_manager=session_manager,
            model=model,
            tool_registry=tool_registry,
            extensions=ext_list,
            skill_loader=skill_loader,
            security_monitor=security_monitor,
            plan_mode_manager=plan_mode_manager,
            auto_mode_manager=auto_mode_manager,
            on_mode_change=self._handle_mode_change,
            on_plan_approval=self._handle_plan_approval,
            on_auto_approval=self._handle_auto_approval,
        )
        if system_prompt:
            kwargs["system_prompt"] = system_prompt
        self._session = AgentSession(**kwargs)
        
        # Wire callbacks to Rich renderer
        self._session.on_token = lambda t: self._renderer.append_token(t)
        self._session.on_tool_call = lambda n, a: self._renderer.render_tool_call(n, a)
        self._session.on_tool_result = lambda n, r: self._renderer.render_tool_result(n, r.output)
        self._session.on_error = lambda m: self._renderer.render_error(m)

    def _get_mode_info(self) -> tuple[str, int | None]:
        return self._current_mode, self._current_phase

    def _register_builtin_commands(self) -> None:
        from codepi.core.commands import Command
        builtins = [
            Command(name="/help", description="Show available commands and shortcuts", category="general"),
            Command(name="/clear", description="Clear the terminal screen", category="general"),
            Command(name="/exit", description="Exit the session", aliases=["/quit"], category="general"),
            Command(name="/model", description="Show or switch the current model", category="general"),
        ]
        for cmd in builtins:
            self._command_registry.register(cmd)

    def _handle_mode_change(self, old_mode: str, new_mode: str) -> None:
        self._current_mode = new_mode
        if self._plan_mode_manager and self._plan_mode_manager.is_active and self._plan_mode_manager.state:
            self._current_phase = self._plan_mode_manager.state.phase.value
        else:
            self._current_phase = None
        self._renderer.render_info(f"Mode changed: {old_mode} → {new_mode}")

    def _handle_plan_approval(self, design: str) -> bool:
        self._renderer.render_info("\n" + "="*60)
        self._renderer.render_info("PLAN REVIEW - Approve this plan?")
        self._renderer.render_info("="*60)
        self._renderer.render_info(design[:2000] + ("..." if len(design) > 2000 else ""))
        self._renderer.render_info("="*60)
        return False  # Don't auto-approve

    def _handle_auto_approval(self, reason: str, operation: str) -> bool:
        self._renderer.render_info(f"Auto mode approval required: {operation} - {reason}")
        return False  # Don't auto-approve

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
