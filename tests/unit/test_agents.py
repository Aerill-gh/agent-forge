from pathlib import Path

from langchain_core.language_models.fake_chat_models import FakeListChatModel

from agentcore.agents import build_agent
from agentcore.llm import ModelRouter
from agentcore.specs.models import IO, AgentSpec, Budget

RAIL_PROMPT = """\
## Role

You are a {{ persona }}.

## Action

Answer directly.

## Information

None.

## Limits

Never fabricate data.
"""


def _fake_spec(prompt_path: str) -> AgentSpec:
    return AgentSpec(
        id="AGT-999",
        title="Fake agent",
        status="draft",
        version="0.1.0",
        owner="@tester",
        model_tier="light",
        prompt_path=prompt_path,
        budget=Budget(max_tokens_per_run=1000, max_usd_per_run=1.0, max_tool_calls=5),
        io=IO(input_schema="x.json", output_schema="y.json"),
    )


def test_build_agent_runs_a_turn_with_fake_model(tmp_path: Path) -> None:
    prompt_dir = tmp_path / "prompts" / "fake"
    prompt_dir.mkdir(parents=True)
    prompt_path = prompt_dir / "fake_system.md"
    prompt_path.write_text(RAIL_PROMPT)

    spec = _fake_spec("prompts/fake/fake_system.md")

    def factory(model_id: str) -> FakeListChatModel:
        return FakeListChatModel(responses=["the final answer"])

    router = ModelRouter(tiers={"light": ["fake:small"]}, model_factory=factory)

    agent = build_agent(spec, router, repo_root=tmp_path, persona="risk analyst")

    result = agent.invoke({"messages": [{"role": "user", "content": "hello"}]})

    assert result["messages"][-1].content == "the final answer"
