from __future__ import annotations
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings


def make_keybindings(
    on_follow_up,
    on_cancel,
    on_clear,
    on_checkpoint,
    on_toggle_plan_mode=None,
    on_toggle_auto_mode=None,
) -> KeyBindings:
    kb = KeyBindings()

    @kb.add("escape", "enter")
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

    @kb.add("c-p")
    def toggle_plan_mode(event):
        if on_toggle_plan_mode:
            on_toggle_plan_mode()

    @kb.add("c-a")
    def toggle_auto_mode(event):
        if on_toggle_auto_mode:
            on_toggle_auto_mode()

    return kb


MODE_COLORS = {
    "normal": "ansigray",
    "plan": "ansicyan",
    "auto": "ansiyellow",
}

PHASE_NAMES = {
    1: "UNDERSTAND",
    2: "DESIGN",
    3: "REVIEW",
    4: "FINALIZE",
    5: "EXIT",
}


def default_toolbar(model: str, session_id: str, mode_info: tuple[str, int | None] | None = None) -> HTML:
    mode, phase = mode_info or ("normal", None)
    mode_str = f'<style fg="{MODE_COLORS.get(mode, "ansigray")}">[{mode.upper()}]</style>'
    if phase and mode == "plan":
        phase_name = PHASE_NAMES.get(phase, f"P{phase}")
        mode_str = f'<style fg="ansicyan">[PLAN:{phase_name}]</style>'
    
    return HTML(
        f"<b>{model}</b>  session: {session_id[:8]}  {mode_str}  "
        f"<i>Enter: send  Alt+Enter: queue  Ctrl+P: plan  Ctrl+A: auto  Ctrl+C: exit</i>"
    )
