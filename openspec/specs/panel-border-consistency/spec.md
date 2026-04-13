## ADDED Requirements

### Requirement: Panel border width consistency
All Rich Panel components rendered by the TUI SHALL have top, bottom, left, and right borders of equal visual width. The Panel's horizontal border segments SHALL align precisely so that the top-left and top-right corners connect seamlessly with the vertical borders.

#### Scenario: Info panel renders with aligned borders
- **WHEN** `render_info("test message")` is called
- **THEN** the top border horizontal line length SHALL equal the bottom border horizontal line length
- **AND** the top-left corner character SHALL connect directly to the left vertical border
- **AND** the top-right corner character SHALL connect directly to the right vertical border

#### Scenario: Error panel renders with aligned borders
- **WHEN** `render_error("error message")` is called
- **THEN** the top border horizontal line length SHALL equal the bottom border horizontal line length

#### Scenario: Warning panel renders with aligned borders
- **WHEN** `render_warning("warning message")` is called
- **THEN** the top border horizontal line length SHALL equal the bottom border horizontal line length

### Requirement: Panel titles use unambiguous-width characters
Panel titles in all TUI render methods SHALL NOT contain emoji characters with ambiguous cell widths. Titles SHALL use either plain ASCII text or Unicode characters with deterministic single-cell widths.

#### Scenario: Title contains no variation selectors
- **WHEN** any Panel title is rendered
- **THEN** the title text SHALL NOT contain Unicode variation selector U+FE0F
- **AND** the title text SHALL NOT contain emoji codepoints that have ambiguous display widths across terminals

#### Scenario: Title retains visual distinction
- **WHEN** a Panel title is rendered with an icon
- **THEN** the icon SHALL be a Unicode character with a well-defined cell width of 1 (e.g., ℹ U+2139, ✓ U+2713, ✕ U+2715)
- **AND** the Panel SHALL still visually distinguish between info, error, warning, and success types via border color and title text
