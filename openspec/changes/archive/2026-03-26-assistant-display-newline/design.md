## Context

The `RichRenderer` class in `codepi/tui/rich_renderer.py` handles terminal output in interactive mode. The flow for assistant responses is:

1. `append_token()` - Streams tokens to console with `end=""` (no trailing newline)
2. `end_turn()` - Collects buffered content into a Panel and displays it

The issue: When streaming tokens don't end with a newline character, the Panel printed in `end_turn()` may not start on a fresh line, causing visual inconsistency.

## Goals / Non-Goals

**Goals:**
- Ensure assistant response Panel always starts on a new line
- Maintain backward compatibility with existing behavior
- Keep the change minimal and focused

**Non-Goals:**
- Changing how streaming works
- Modifying other Panel renderings (user messages, tool calls, etc.)
- Adding configuration options for this behavior

## Decisions

### Decision 1: Print newline before Panel in `end_turn()`

**Approach**: Add `self.console.print()` before the Panel to ensure we're on a fresh line.

**Rationale**: 
- Simple, reliable approach that works regardless of streaming state
- Rich's `console.print()` with no arguments just prints a newline
- No impact on the Panel content itself

**Alternatives considered**:
- Checking if buffer ends with newline → More complex, less reliable with Rich's soft wrap
- Clearing the line → Would lose visible streaming output, bad UX
- Using `console.line()` → Same effect as empty print, but less idiomatic

### Decision 2: Placement of newline

**Location**: Inside `end_turn()`, immediately before the Panel is printed.

**Rationale**:
- Keeps the fix localized to where the issue manifests
- Doesn't affect `append_token()` which handles streaming correctly
- Clear semantic meaning: "ensure clean line before Panel"

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Extra blank line if streaming ended cleanly | Acceptable trade-off for consistent formatting |
| Minimal visual change may go unnoticed | This is fine - the fix addresses a bug, not a feature |

## Migration Plan

Not applicable - this is a simple one-line fix with no migration needed.
