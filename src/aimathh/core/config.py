"""Global harness configuration (environment + .env file)."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    """All tunable harness settings. Override via environment or .env."""

    model_config = SettingsConfigDict(env_prefix="AIMATHH_", env_file=".env", extra="ignore")

    env: str = "dev"
    data_dir: Path = Field(default=_REPO_ROOT / "data")
    artifact_dir: Path = Field(default=_REPO_ROOT / "data" / "artifacts")
    db_path: Path = Field(default=_REPO_ROOT / "data" / "aimathh.db")
    sandbox_root: Path = Field(default=_REPO_ROOT / "data" / "sandbox")
    log_level: str = "INFO"

    # Model providers
    openai_base_url: str = "https://api.openai.com/v1"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    anthropic_base_url: str = "https://api.anthropic.com"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-5-sonnet-latest"
    ollama_base_url: str = "http://localhost:11434"
    local_model: str = ""

    # Sandbox defaults
    default_timeout_s: int = 120
    max_memory_mb: int = 2048
    allow_network: bool = False
    allow_install: bool = False

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        self.sandbox_root.mkdir(parents=True, exist_ok=True)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    s = Settings()
    # Resolve relative paths against CWD for predictable behaviour.
    for attr in ("data_dir", "artifact_dir", "db_path", "sandbox_root"):
        p = getattr(s, attr)
        if not isinstance(p, Path):
            p = Path(p)
        if not p.is_absolute():
            setattr(s, attr, (Path(os.getcwd()) / p).resolve())
    return s
