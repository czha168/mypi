from __future__ import annotations
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from mypi.tui.components import default_toolbar
from mypi.tui.renderer import StreamingRenderer
from rich.console import Console


class TUIApp:
    def __init__(self, model: str, session_id: str):
        self.model = model
        self.session_id = session_id
        self.console = Console()
        self.renderer = StreamingRenderer(console=self.console)
        self._prompt_session = PromptSession(
            history=InMemoryHistory(),
            bottom_toolbar=lambda: default_toolbar(self.model, self.session_id),
        )

    async def get_input(self, prompt: str = "> ") -> str:
        return await self._prompt_session.prompt_async(prompt)
