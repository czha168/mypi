from __future__ import annotations
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from mypi.tui.components import make_keybindings, default_toolbar
from mypi.tui.renderer import StreamingRenderer
from rich.console import Console


class TUIApp:
    def __init__(
        self,
        model: str,
        session_id: str,
        on_submit=None,
        on_follow_up=None,
        on_cancel=None,
        on_clear=None,
        on_checkpoint=None,
    ):
        self.model = model
        self.session_id = session_id
        self.console = Console()
        self.renderer = StreamingRenderer(console=self.console)

        # Use no-ops for unset callbacks
        kb = make_keybindings(
            on_submit=on_submit or (lambda t: None),
            on_follow_up=on_follow_up or (lambda t: None),
            on_cancel=on_cancel or (lambda: None),
            on_clear=on_clear or (lambda: None),
            on_checkpoint=on_checkpoint or (lambda: None),
        )
        self._prompt_session = PromptSession(
            history=InMemoryHistory(),
            bottom_toolbar=lambda: default_toolbar(self.model, self.session_id),
            key_bindings=kb,
        )

    async def get_input(self, prompt: str = "> ") -> str:
        return await self._prompt_session.prompt_async(prompt)
