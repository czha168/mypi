"""OpenSpec artifact templates — loaded by skills when generating artifacts."""

from __future__ import annotations
from pathlib import Path

ARTIFACT_DIR = Path(__file__).parent

TEMPLATES: dict[str, str] = {
    "proposal": (ARTIFACT_DIR / "proposal.md").read_text(),
    "spec": (ARTIFACT_DIR / "spec.md").read_text(),
    "design": (ARTIFACT_DIR / "design.md").read_text(),
    "tasks": (ARTIFACT_DIR / "tasks.md").read_text(),
}
