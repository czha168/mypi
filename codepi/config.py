from __future__ import annotations
import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_CONFIG_PATH = Path.home() / ".codepi" / "config.toml"

DEFAULT_CONFIG = """
[provider]
base_url = "https://api.openai.com/v1"
api_key  = ""
model    = "gpt-4o"

[session]
compaction_threshold = 0.50
max_retries = 3

[paths]
sessions_dir  = "~/.codepi/sessions"
skills_dir    = "~/.codepi/skills"
extensions_dir = "~/.codepi/extensions"

[lsp]
server = ""  # "pyright", "pylsp", "jedi-language-server", or empty for auto-detect
enabled = true

[security]
enabled = true
# rule_overrides = { "shared:push" = "allow" }

[modes.plan]
enabled = false
auto_advance = false
require_explicit_approval = true
max_iterations = 5

[modes.auto]
enabled = false
max_iterations = 100
require_approval_for = ["push", "pr", "publish"]
pause_on_errors = true
auto_run_tests = true

[memory]
enabled = true
max_items = 500
injection_token_budget = 1000
hotness_half_life_days = 7
dedup_jaccard_threshold = 0.7
"""


@dataclass
class ProviderConfig:
    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    model: str = "gpt-4o"


@dataclass
class SessionConfig:
    compaction_threshold: float = 0.50
    max_retries: int = 3


@dataclass
class PathsConfig:
    sessions_dir: Path = field(default_factory=lambda: Path.home() / ".codepi" / "sessions")
    skills_dir: Path = field(default_factory=lambda: Path.home() / ".codepi" / "skills")
    extensions_dir: Path = field(default_factory=lambda: Path.home() / ".codepi" / "extensions")


@dataclass
class LSPConfig:
    server: str = ""  # empty = auto-detect (pyright → pylsp → jedi-language-server)
    enabled: bool = True


@dataclass
class SecurityConfig:
    enabled: bool = True
    rule_overrides: dict[str, str] = field(default_factory=dict)


@dataclass
class PlanModeConfigData:
    """Configuration for plan mode."""
    enabled: bool = False
    auto_advance: bool = False
    require_explicit_approval: bool = True
    max_iterations: int = 5


@dataclass
class AutoModeConfigData:
    """Configuration for auto mode."""
    enabled: bool = False
    max_iterations: int = 100
    require_approval_for: list[str] = field(default_factory=lambda: ["push", "pr", "publish"])
    pause_on_errors: bool = True
    auto_run_tests: bool = True


@dataclass
class MemoryConfig:
    enabled: bool = True
    max_items: int = 500
    injection_token_budget: int = 1000
    hotness_half_life_days: int = 7
    dedup_jaccard_threshold: float = 0.7


@dataclass
class ModesConfig:
    """Configuration for operation modes."""
    plan: PlanModeConfigData = field(default_factory=PlanModeConfigData)
    auto: AutoModeConfigData = field(default_factory=AutoModeConfigData)


@dataclass
class Config:
    provider: ProviderConfig = field(default_factory=ProviderConfig)
    session: SessionConfig = field(default_factory=SessionConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)
    lsp: LSPConfig = field(default_factory=LSPConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    modes: ModesConfig = field(default_factory=ModesConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)


def load_config(config_path: Path | None = None) -> Config:
    path = config_path or DEFAULT_CONFIG_PATH
    raw: dict = {}
    if path.exists():
        with path.open("rb") as f:
            raw = tomllib.load(f)

    p = raw.get("provider", {})
    s = raw.get("session", {})
    paths = raw.get("paths", {})
    l = raw.get("lsp", {})
    sec = raw.get("security", {})
    modes_raw = raw.get("modes", {})
    plan_raw = modes_raw.get("plan", {})
    auto_raw = modes_raw.get("auto", {})
    mem = raw.get("memory", {})

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
            compaction_threshold=s.get("compaction_threshold", 0.50),
            max_retries=s.get("max_retries", 3),
        ),
        paths=PathsConfig(
            sessions_dir=Path(paths.get("sessions_dir", "~/.codepi/sessions")).expanduser(),
            skills_dir=Path(paths.get("skills_dir", "~/.codepi/skills")).expanduser(),
            extensions_dir=Path(paths.get("extensions_dir", "~/.codepi/extensions")).expanduser(),
        ),
        lsp=LSPConfig(
            server=l.get("server", ""),
            enabled=l.get("enabled", True),
        ),
        security=SecurityConfig(
            enabled=sec.get("enabled", True),
            rule_overrides=sec.get("rule_overrides", {}),
        ),
        modes=ModesConfig(
            plan=PlanModeConfigData(
                enabled=plan_raw.get("enabled", False),
                auto_advance=plan_raw.get("auto_advance", False),
                require_explicit_approval=plan_raw.get("require_explicit_approval", True),
                max_iterations=plan_raw.get("max_iterations", 5),
            ),
            auto=AutoModeConfigData(
                enabled=auto_raw.get("enabled", False),
                max_iterations=auto_raw.get("max_iterations", 100),
                require_approval_for=auto_raw.get("require_approval_for", ["push", "pr", "publish"]),
                pause_on_errors=auto_raw.get("pause_on_errors", True),
                auto_run_tests=auto_raw.get("auto_run_tests", True),
            ),
        ),
        memory=MemoryConfig(
            enabled=mem.get("enabled", True),
            max_items=mem.get("max_items", 500),
            injection_token_budget=mem.get("injection_token_budget", 1000),
            hotness_half_life_days=mem.get("hotness_half_life_days", 7),
            dedup_jaccard_threshold=mem.get("dedup_jaccard_threshold", 0.7),
        ),
    )
