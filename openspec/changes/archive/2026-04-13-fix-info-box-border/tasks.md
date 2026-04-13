## 1. Fix Panel Title Characters

- [x] 1.1 In `codepi/tui/rich_renderer.py`, update `render_info` title from `"ℹ️  Info"` to `"ℹ Info"` (remove U+FE0F variation selector)
- [x] 1.2 Update `render_error` title from `"❌ Error"` to `"✕ Error"` (replace emoji with U+2715)
- [x] 1.3 Update `render_warning` title from `"⚠️  Warning"` to `"⚠ Warning"` (remove U+FE0F variation selector)
- [x] 1.4 Verify `render_success` title `"✓ Success"` — confirm ✓ (U+2713) renders with consistent width; update if needed
- [x] 1.5 Verify `render_tool_result` title `"✓ {tool_name} Result"` — same check as 1.4

## 2. Visual Verification

- [x] 2.1 Run codepi in interactive TUI mode and trigger `render_info` — verify all four borders align
- [x] 2.2 Trigger `render_error` — verify border alignment
- [x] 2.3 Trigger `render_warning` — verify border alignment
- [x] 2.4 Trigger `render_success` — verify border alignment
- [x] 2.5 Run existing tests: `python3 -m pytest tests/tui/ -v`
