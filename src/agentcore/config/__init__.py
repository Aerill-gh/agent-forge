"""Layered app config, per ADR-004.

Precedence (lowest to highest): field defaults -> `configs/environments/
<env>.yaml` -> environment variables. Secrets (API keys) are never read
from YAML — only from env vars (`AGENTCORE_*`), held as `SecretStr`.
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AGENTCORE_", extra="ignore")

    env: str = "local"
    langsmith_api_key: SecretStr | None = None
    anthropic_api_key: SecretStr | None = None
    openai_api_key: SecretStr | None = None


def load_config(configs_dir: str | Path = "configs") -> AppConfig:
    """Build AppConfig: defaults, then the environment YAML, then env vars."""
    env_provided = AppConfig()  # picks up AGENTCORE_* env vars automatically

    env_name = os.environ.get("AGENTCORE_ENV", env_provided.env)
    yaml_path = Path(configs_dir) / "environments" / f"{env_name}.yaml"
    yaml_defaults: dict[str, object] = {}
    if yaml_path.is_file():
        loaded = yaml.safe_load(yaml_path.read_text()) or {}
        if isinstance(loaded, dict):
            yaml_defaults = loaded

    merged = {**yaml_defaults, **env_provided.model_dump(exclude_unset=True)}
    return AppConfig(**merged)
