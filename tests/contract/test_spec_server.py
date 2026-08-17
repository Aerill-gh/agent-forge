import shutil
from pathlib import Path

import pytest

from servers.spec_server.server import server

REPO_ROOT = Path(__file__).resolve().parents[2]

_EXPECTED_TOOLS = {
    "spec_for_target",
    "spec_get",
    "spec_search",
    "spec_create",
    "next_task",
    "bind_test",
    "scaffold_agent",
    "spec_lint",
}


@pytest.mark.asyncio
async def test_tool_budget_and_names() -> None:
    tools = await server.list_tools()
    names = {t.name for t in tools}

    assert names == _EXPECTED_TOOLS
    assert len(names) <= 8


@pytest.mark.asyncio
async def test_spec_for_target_resolves_via_call_tool() -> None:
    result = await server.call_tool(
        "spec_for_target",
        {
            "target": "src/agentcore/mcp/__init__.py",
            "specs_dir": "specs",
            "repo_root": str(REPO_ROOT),
        },
    )

    assert result.structured_content == {"spec_id": "ADR-005"}


@pytest.mark.asyncio
async def test_spec_get_returns_full_model() -> None:
    result = await server.call_tool(
        "spec_get", {"spec_id": "ADR-005", "specs_dir": str(REPO_ROOT / "specs")}
    )

    assert result.structured_content["id"] == "ADR-005"
    assert result.structured_content["status"] == "approved"


@pytest.mark.asyncio
async def test_spec_lint_tool_reports_clean_repo() -> None:
    result = await server.call_tool(
        "spec_lint", {"specs_dir": str(REPO_ROOT / "specs"), "repo_root": str(REPO_ROOT)}
    )

    assert result.structured_content["failures"] == []


@pytest.mark.asyncio
async def test_scaffold_agent_refuses_without_approved_spec(tmp_path: Path) -> None:
    specs_dir = tmp_path / "specs"
    (specs_dir / "agents").mkdir(parents=True)
    draft_agent = """\
---
id: AGT-950
title: Draft agent
status: draft
version: 0.1.0
owner: "@tester"
model_tier: light
prompt_path: "prompts/fake/fake_system.md"
budget: { max_tokens_per_run: 1, max_usd_per_run: 0.1, max_tool_calls: 1 }
io: { input_schema: "x.json", output_schema: "y.json" }
governs:
  paths:
    - "src/agents/fake/**"
---
"""
    (specs_dir / "agents" / "AGT-950.md").write_text(draft_agent)

    result = await server.call_tool(
        "scaffold_agent",
        {"spec_id": "AGT-950", "specs_dir": str(specs_dir), "repo_root": str(tmp_path)},
    )

    assert "error" in result.structured_content
    assert "not approved" in result.structured_content["error"]
    assert not (tmp_path / "src" / "agents" / "fake").exists()


@pytest.mark.asyncio
async def test_spec_create_scaffolds_from_template(tmp_path: Path) -> None:
    specs_dir = tmp_path / "specs"
    shutil.copytree(REPO_ROOT / "specs" / "templates", specs_dir / "templates")

    result = await server.call_tool(
        "spec_create",
        {
            "kind": "ADR",
            "spec_id": "ADR-999",
            "title": "Test decision",
            "specs_dir": str(specs_dir),
        },
    )

    assert result.structured_content["created"] is True
    created_path = Path(result.structured_content["path"])
    assert created_path.is_file()
    assert "ADR-999" in created_path.read_text()
