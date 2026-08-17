"""ModelRouter: tier -> chat model, per ADR-004.

Provider-agnostic: model construction goes through an injectable
`model_factory` (defaults to `langchain.chat_models.init_chat_model`), so
"all API adapters" falls out of one function instead of a class per
provider. Each tier is a fallback chain — the router tries each
`"provider:model"` string in order and returns the first that constructs
and (optionally) invokes successfully.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml
from langchain_core.language_models.chat_models import BaseChatModel

ModelFactory = Callable[[str], BaseChatModel]


class NoModelAvailable(Exception):
    """Raised when every model in a tier's fallback chain failed."""


def _default_factory(model_id: str) -> BaseChatModel:
    from langchain.chat_models import init_chat_model

    return init_chat_model(model_id)


class ModelRouter:
    """Resolves an `AGT-` spec's `model_tier` to a chat model.

    `tiers` maps tier name -> ordered fallback chain of
    `"provider:model"` strings, typically loaded from `models.yaml`.
    """

    def __init__(
        self,
        tiers: dict[str, list[str]],
        model_factory: ModelFactory | None = None,
    ) -> None:
        self.tiers = tiers
        self._model_factory = model_factory or _default_factory

    @classmethod
    def from_yaml(cls, path: str | Path, model_factory: ModelFactory | None = None) -> ModelRouter:
        data: dict[str, Any] = yaml.safe_load(Path(path).read_text()) or {}
        tiers = data.get("tiers", {})
        return cls(tiers=tiers, model_factory=model_factory)

    def for_tier(self, tier: str) -> BaseChatModel:
        chain = self.tiers.get(tier)
        if not chain:
            raise NoModelAvailable(f"no fallback chain configured for tier {tier!r}")

        errors: list[str] = []
        for model_id in chain:
            try:
                return self._model_factory(model_id)
            except Exception as exc:  # noqa: BLE001 — deliberately broad: any model in the chain may fail
                errors.append(f"{model_id}: {exc}")

        raise NoModelAvailable(f"every model in tier {tier!r} failed: " + "; ".join(errors))
