"""Agent factory: spec in, compiled LangGraph agent out, per ADR-004.

Tool wiring (`TOOL-`/MCP allowlists) is P4 — `build_agent` compiles with
`tools=[]` until then. The caller supplies a `ModelRouter` (built from
whatever `models.yaml` and provider credentials the environment has)
rather than `build_agent` constructing one itself, so tests can inject a
fake model factory without touching real config.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from langchain.agents import create_agent

from agentcore.llm import ModelRouter
from agentcore.prompts import render_prompt
from agentcore.specs.models import AgentSpec


def build_agent(
    spec: AgentSpec,
    router: ModelRouter,
    repo_root: str | Path = ".",
    **prompt_context: object,
) -> Any:
    """Build a compiled LangGraph agent from an AGT- spec."""
    model = router.for_tier(spec.model_tier)
    prompt_path = Path(repo_root) / spec.prompt_path
    system_prompt = render_prompt(prompt_path, **prompt_context)
    return create_agent(model, tools=[], system_prompt=system_prompt, name=spec.id)
