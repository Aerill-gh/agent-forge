import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from agentcore.llm import ModelRouter, NoModelAvailable


def test_router_resolves_tier_via_factory() -> None:
    def factory(model_id: str) -> FakeListChatModel:
        return FakeListChatModel(responses=[f"response from {model_id}"])

    router = ModelRouter(tiers={"light": ["fake:small"]}, model_factory=factory)

    model = router.for_tier("light")

    assert model.invoke("hi").content == "response from fake:small"


def test_router_falls_back_on_primary_failure() -> None:
    calls: list[str] = []

    def factory(model_id: str) -> FakeListChatModel:
        calls.append(model_id)
        if model_id == "fake:primary":
            raise RuntimeError("primary provider is down")
        return FakeListChatModel(responses=["fallback response"])

    router = ModelRouter(
        tiers={"versatile": ["fake:primary", "fake:secondary"]}, model_factory=factory
    )

    model = router.for_tier("versatile")

    assert model.invoke("hi").content == "fallback response"
    assert calls == ["fake:primary", "fake:secondary"]


def test_router_raises_when_every_model_in_chain_fails() -> None:
    def factory(model_id: str) -> FakeListChatModel:
        raise RuntimeError(f"{model_id} unavailable")

    router = ModelRouter(tiers={"light": ["fake:a", "fake:b"]}, model_factory=factory)

    with pytest.raises(NoModelAvailable):
        router.for_tier("light")


def test_router_raises_for_unknown_tier() -> None:
    router = ModelRouter(tiers={})

    with pytest.raises(NoModelAvailable):
        router.for_tier("reasoning")
