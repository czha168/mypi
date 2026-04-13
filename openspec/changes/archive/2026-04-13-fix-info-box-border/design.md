## Context

codepi's TUI uses Rich's `Panel` component for all info, error, warning, success, and tool result displays. Each panel includes a title containing emoji characters (ℹ️, ❌, ⚠️, ✓). The top border of these panels renders one character shorter than the side and bottom borders, creating a visually broken appearance.

The root cause is emoji character width miscalculation. Rich's `Panel` calculates the top border width accounting for the title text's `cell_len`. Emojis like "ℹ️" (U+2139 + U+FE0F) have ambiguous display widths — Rich may measure them as 1 cell while the terminal renders them as 2 cells, or vice versa. This causes the horizontal rule segments around the title to be off by 1 character.

Affected methods in `codepi/tui/rich_renderer.py`:
- `render_info` — title: `"ℹ️  Info"`
- `render_error` — title: `"❌ Error"`
- `render_warning` — title: `"⚠️  Warning"`
- `render_success` — title: `"✓ Success"` (less likely affected, ✓ is typically 1-width)
- `render_tool_result` — title: `"✓ {tool_name} Result"`

## Goals / Non-Goals

**Goals:**
- Fix the info box top border to align exactly with the side and bottom borders
- Ensure all Panel-based renderings have consistent border widths
- Maintain the current visual style (colored borders, titled panels)

**Non-Goals:**
- Changing the Panel layout or styling aesthetic
- Adding new rendering capabilities
- Switching away from Rich's Panel component

## Decisions

### Decision 1: Replace emoji titles with plain-text equivalents

**Choice**: Replace emoji characters in Panel titles with ASCII/Unicode characters that have unambiguous cell widths.

**Rationale**: Rich's emoji width handling varies across terminals and Rich versions. The most robust fix eliminates the ambiguity entirely by using characters with deterministic widths.

**Mapping**:
- `"ℹ️  Info"` → `"ℹ Info"` (remove variation selector U+FE0F) or use `"Info"` without emoji
- `"❌ Error"` → `"✕ Error"` or `"Error"`
- `"⚠️  Warning"` → `"⚠ Warning"` (remove variation selector) or `"Warning"`
- `"✓ Success"` → already uses ✓ (typically safe, but verify)

**Alternatives considered**:
1. **Set explicit Panel `width`** — Forces correct total width but doesn't fix the internal title padding calculation; Rich still miscalculates the title space.
2. **Use `title_align="left"` with padding adjustment** — Doesn't address the root cause; just shifts where the misalignment appears.
3. **Upgrade Rich** — May fix in newer versions, but not all terminals handle emoji width the same way regardless of Rich version.

### Decision 2: Use Unicode symbols without variation selectors

**Choice**: Keep the visual iconography but use characters that have well-defined widths. Remove variation selectors (U+FE0F) from emoji, or use plain Unicode symbols (ℹ, ⚠, ✓, ✕).

**Rationale**: The variation selector (U+FE0F) is what causes width ambiguity — it tells the terminal to render the preceding character as an emoji (potentially 2-width) vs. text (1-width). Removing it forces text-style rendering with predictable width.

## Risks / Trade-offs

- **[Terminal-specific rendering]** → Some terminals may display the base character differently without the variation selector. Mitigate by testing across common terminals (iTerm2, Terminal.app, Windows Terminal, Alacritty).
- **[Visual regression]** → Icons may look slightly different without emoji rendering. This is acceptable — consistency matters more than emoji aesthetics in a terminal tool.
