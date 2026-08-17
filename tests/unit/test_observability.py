import pytest

from agentcore.observability import MissingLangSmithEndpoint, configure_langsmith
from agentcore.specs.models import OpsSpec


def _ops(**overrides: object) -> OpsSpec:
    defaults: dict[str, object] = {
        "id": "OPS-900",
        "title": "Fake ops",
        "status": "draft",
        "version": "0.1.0",
        "owner": "@tester",
        "deploy_target": "self_hosted",
    }
    defaults.update(overrides)
    return OpsSpec(**defaults)  # type: ignore[arg-type]


def test_configure_langsmith_per_target(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LANGCHAIN_ENDPOINT", raising=False)

    cloud_env = configure_langsmith(_ops(langsmith_target="cloud"))
    assert cloud_env["LANGCHAIN_ENDPOINT"] == "https://api.smith.langchain.com"
    assert cloud_env["LANGCHAIN_PROJECT"] == "OPS-900"
    assert cloud_env["LANGCHAIN_TRACING_V2"] == "true"

    self_hosted_env = configure_langsmith(
        _ops(langsmith_target="self_hosted", langsmith_endpoint="https://langsmith.internal")
    )
    assert self_hosted_env["LANGCHAIN_ENDPOINT"] == "https://langsmith.internal"

    with pytest.raises(MissingLangSmithEndpoint):
        configure_langsmith(_ops(langsmith_target="self_hosted"))
