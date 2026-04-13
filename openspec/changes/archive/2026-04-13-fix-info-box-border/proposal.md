## Why

The info box rendered in TUI mode has a visual alignment bug: the top border is one character shorter than the side and bottom borders, creating an asymmetric, visually broken panel. This is caused by an emoji character width mismatch in Rich Panel title rendering.

## What Changes

- Fix the `render_info` method in `codepi/tui/rich_renderer.py` to ensure the Panel top border width matches the rest of the box
- Audit all other Panel-based render methods (`render_error`, `render_warning`, `render_success`, `render_tool_result`) that use emoji titles for the same border width issue

## Capabilities

### New Capabilities
- `panel-border-consistency`: Ensure all Rich Panel borders render with consistent width across top, sides, and bottom, regardless of title content (emoji, wide characters, etc.)

### Modified Capabilities

## Impact

- `codepi/tui/rich_renderer.py` — The `render_info` method and potentially other Panel render methods with emoji titles
- No API or dependency changes — this is a pure visual fix
- No breaking changes
