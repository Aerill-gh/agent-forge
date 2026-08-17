from pathlib import Path

import pytest

from agentcore.config import load_config


def test_load_config_layers_and_env_wins(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "environments").mkdir()
    (tmp_path / "environments" / "local.yaml").write_text("env: local\n")

    monkeypatch.delenv("AGENTCORE_ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("AGENTCORE_ENV", raising=False)
    cfg = load_config(tmp_path)
    assert cfg.env == "local"
    assert cfg.anthropic_api_key is None

    monkeypatch.setenv("AGENTCORE_ANTHROPIC_API_KEY", "sk-from-env")
    cfg = load_config(tmp_path)
    assert cfg.anthropic_api_key is not None
    assert cfg.anthropic_api_key.get_secret_value() == "sk-from-env"


def test_load_config_missing_yaml_falls_back_to_defaults(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("AGENTCORE_ENV", raising=False)
    cfg = load_config(tmp_path / "does-not-exist")
    assert cfg.env == "local"
