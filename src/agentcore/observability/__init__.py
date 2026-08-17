"""LangSmith tracing wiring, per ADR-004.

Reads an `OPS-` spec's `langsmith_target` and sets the LANGCHAIN_*
env vars LangChain/LangGraph read to enable tracing. Every generated
project traces somewhere — `cloud` or `self_hosted` — per the plan's
§12 locked configuration reference; there is no "off" option.
"""

from __future__ import annotations

import os

from agentcore.specs.models import OpsSpec

_CLOUD_ENDPOINT = "https://api.smith.langchain.com"


class MissingLangSmithEndpoint(Exception):
    """Raised when langsmith_target=self_hosted but langsmith_endpoint is unset."""


def configure_langsmith(ops: OpsSpec) -> dict[str, str]:
    """Set LANGCHAIN_TRACING_V2/LANGCHAIN_PROJECT/LANGCHAIN_ENDPOINT from ops.

    Returns the env vars that were set, for inspection/testing.
    """
    if ops.langsmith_target == "self_hosted":
        if not ops.langsmith_endpoint:
            raise MissingLangSmithEndpoint(
                "OPS spec langsmith_target=self_hosted requires langsmith_endpoint"
            )
        endpoint = ops.langsmith_endpoint
    else:
        endpoint = _CLOUD_ENDPOINT

    env = {
        "LANGCHAIN_TRACING_V2": "true",
        "LANGCHAIN_PROJECT": ops.id,
        "LANGCHAIN_ENDPOINT": endpoint,
    }
    os.environ.update(env)
    return env
