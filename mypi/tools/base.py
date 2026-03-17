from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolResult:
    output: str = ""
    error: str | None = None
    metadata: dict = field(default_factory=dict)
