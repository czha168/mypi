from __future__ import annotations
import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_CONFIG_PATH = Path.home() / ".mypi" / "config.toml"

DEFAULT_CONFIG = """
[provider]
base_url = "https://api.openai.com/v1"
api_key  = ""
model    = "gpt-4o"

[session]
compaction_threshold = 0.80
max_retries = 3

[paths]
sessions_dir  = "~/.mypi/sessions"
skills_dir    = "~/.mypi/skills"
extensions_dir = "~/.mypi/extensions"
"""


@dataclass
class ProviderConfig:
    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    model: str = "gpt-4o"


@dataclass
class SessionConfig:
    compaction_threshold: float = 0.80
    max_retries: int = 3


@dataclass
class PathsConfig:
    sessions_dir: Path = field(default_factory=lambda: Path.home() / ".mypi" / "sessions")
    skills_dir: Path = field(default_factory=lambda: Path.home() / ".mypi" / "skills")
    extensions_dir: Path = field(default_factory=lambda: Path.home() / ".mypi" / "extensions")


@dataclass
class Config:
    provider: ProviderConfig = field(default_factory=ProviderConfig)
    session: SessionConfig = field(default_factory=SessionConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)


def load_config(config_path: Path | None = None) -> Config:
    path = config_path or DEFAULT_CONFIG_PATH
    raw: dict = {}
    if path.exists():
        with path.open("rb") as f:
            raw = tomllib.load(f)

    p = raw.get("provider", {})
    s = raw.get("session", {})
    paths = raw.get("paths", {})

    # Environment variables override config file
    api_key = os.environ.get("OPENAI_API_KEY") or p.get("api_key", "")
    base_url = os.environ.get("OPENAI_BASE_URL") or p.get("base_url", "https://api.openai.com/v1")

    return Config(
        provider=ProviderConfig(
            base_url=base_url,
            api_key=api_key,
            model=p.get("model", "gpt-4o"),
        ),
        session=SessionConfig(
            compaction_threshold=s.get("compaction_threshold", 0.80),
            max_retries=s.get("max_retries", 3),
        ),
        paths=PathsConfig(
            sessions_dir=Path(paths.get("sessions_dir", "~/.mypi/sessions")).expanduser(),
            skills_dir=Path(paths.get("skills_dir", "~/.mypi/skills")).expanduser(),
            extensions_dir=Path(paths.get("extensions_dir", "~/.mypi/extensions")).expanduser(),
        ),
    )
