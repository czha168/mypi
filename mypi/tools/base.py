from dataclasses import dataclass, field


@dataclass
class ToolResult:
    output: str = ""
    error: str | None = None
    metadata: dict = field(default_factory=dict)
