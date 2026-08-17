import subprocess
from pathlib import Path

import yaml

from agentcore.specs.agents_md import check_agents_md, sync_agents_md

REPO_ROOT = Path(__file__).resolve().parents[2]

CON_SPEC = """\
---
id: CON-800
title: Fake constitution
status: approved
version: 1.0.0
owner: "@tester"
governs:
  paths:
    - "**"
---
"""

AGT_SPEC = """\
---
id: AGT-800
title: Fake agent
status: draft
version: 0.1.0
owner: "@tester"
model_tier: light
budget: { max_tokens_per_run: 1, max_usd_per_run: 0.1, max_tool_calls: 1 }
io: { input_schema: "x.json", output_schema: "y.json" }
governs:
  paths:
    - "src/agents/fake/node.py"
---
"""

TOOL_SPEC = """\
---
id: TOOL-800
title: Fake tool
status: draft
version: 0.1.0
owner: "@tester"
governs:
  paths:
    - "src/agents/fake/other.py"
---
"""


def _init_repo(repo_root: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=repo_root, check=True)
    subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=repo_root, check=True)
    subprocess.run(["git", "config", "user.name", "tester"], cwd=repo_root, check=True)


def _commit_all(repo_root: Path) -> None:
    subprocess.run(["git", "add", "-A"], cwd=repo_root, check=True)


def _fixture_repo(tmp_path: Path) -> Path:
    _init_repo(tmp_path)
    (tmp_path / "specs").mkdir()
    (tmp_path / "specs" / "CON-800.md").write_text(CON_SPEC)
    (tmp_path / "specs" / "AGT-800.md").write_text(AGT_SPEC)
    (tmp_path / "specs" / "TOOL-800.md").write_text(TOOL_SPEC)
    agents_dir = tmp_path / "src" / "agents" / "fake"
    agents_dir.mkdir(parents=True)
    (agents_dir / "node.py").write_text("# node\n")
    (agents_dir / "other.py").write_text("# other\n")
    _commit_all(tmp_path)
    return tmp_path


def test_sync_writes_one_agents_md_per_governed_directory(tmp_path: Path) -> None:
    repo_root = _fixture_repo(tmp_path)

    written = sync_agents_md(repo_root / "specs", repo_root)

    paths = {p for p, _ in written}
    assert repo_root / "src" / "agents" / "fake" / "AGENTS.md" in paths
    assert (repo_root / "src" / "agents" / "fake" / "AGENTS.md").is_file()


def test_sync_lists_all_owning_specs_for_mixed_directory(tmp_path: Path) -> None:
    repo_root = _fixture_repo(tmp_path)

    written = dict(sync_agents_md(repo_root / "specs", repo_root))
    content = written[repo_root / "src" / "agents" / "fake" / "AGENTS.md"]

    assert "AGT-800" in content
    assert "TOOL-800" in content
    assert "node.py` -> `AGT-800`" in content
    assert "other.py` -> `TOOL-800`" in content


def test_check_flags_stale_agents_md(tmp_path: Path) -> None:
    repo_root = _fixture_repo(tmp_path)
    sync_agents_md(repo_root / "specs", repo_root)

    target = repo_root / "src" / "agents" / "fake" / "AGENTS.md"
    target.write_text("stale content\n")

    stale = check_agents_md(repo_root / "specs", repo_root)

    assert any(s.path == target and s.reason == "outdated" for s in stale)


def test_repo_agents_md_is_in_sync() -> None:
    stale = check_agents_md(REPO_ROOT / "specs", REPO_ROOT)

    assert stale == [], "\n".join(f"{s.path}: {s.reason}" for s in stale)


def test_spec_workflow_skill_frontmatter_names_governed_roots() -> None:
    skill_path = REPO_ROOT / ".claude" / "skills" / "spec-workflow" / "SKILL.md"
    text = skill_path.read_text()
    assert text.startswith("---\n")
    frontmatter = text.split("---\n", 2)[1]
    meta = yaml.safe_load(frontmatter)

    assert meta["name"] == "spec-workflow"
    description = meta["description"]
    for root in ("src/", "prompts/", "tests/", "configs/", "deploy/"):
        assert root in description
    for kind in ("AGT-", "GRP-", "TOOL-", "DS-", "EVL-", "OPS-", "ADR-"):
        assert kind in description
