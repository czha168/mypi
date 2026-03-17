from __future__ import annotations
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings


def make_keybindings(
    on_follow_up,
    on_cancel,
    on_clear,
    on_checkpoint,
) -> KeyBindings:
    kb = KeyBindings()

    @kb.add("escape", "enter")  # Alt+Enter
    def follow_up(event):
        buf = event.app.current_buffer
        text = buf.text
        buf.reset()
        on_follow_up(text)

    @kb.add("escape")
    def cancel(event):
        on_cancel()

    @kb.add("c-l")
    def clear(event):
        on_clear()
        event.app.renderer.clear()

    @kb.add("c-s")
    def checkpoint(event):
        on_checkpoint()

    return kb


def default_toolbar(model: str, session_id: str) -> HTML:
    return HTML(f"<b>{model}</b>  session: {session_id[:8]}  <i>Enter: send  Alt+Enter: queue  Ctrl+C: exit</i>")
