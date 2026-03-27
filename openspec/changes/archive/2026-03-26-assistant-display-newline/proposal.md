## Why

When streaming assistant responses in interactive mode, tokens are printed to the console in real-time. After streaming completes, `end_turn()` displays the full response in a Panel. Currently, if the streaming output doesn't end with a newline, the Panel may not start on a fresh line, causing visual formatting issues where the Panel continues from the previous line instead of starting cleanly on a new line.

## What Changes

- Modify `RichRenderer.end_turn()` to print a newline before rendering the assistant Panel
- This ensures the Panel always starts on a new line regardless of where streaming tokens ended

## Capabilities

### New Capabilities

- `assistant-display-formatting`: Ensures assistant response panels always start on a fresh line in interactive mode, improving visual clarity and consistency

### Modified Capabilities

None. This is a UI formatting fix that doesn't change existing spec-level behavior.

## Impact

- **Affected file**: `codepi/tui/rich_renderer.py`
- **Affected method**: `RichRenderer.end_turn()`
- **User-visible change**: Assistant response panels will always appear on a new line
- **No breaking changes**: Only affects visual formatting, no API or behavior changes
