import subprocess
from pathlib import Path

from agentcore.specs.index import build_index
from agentcore.specs.resolve import resolve

REPO_ROOT = Path(__file__).resolve().parents[2]

CON_SPEC = """\
---
id: CON-900
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
id: AGT-900
title: Fake agent
status: draft
version: 0.1.0
owner: "@tester"
model_tier: light
budget: { max_tokens_per_run: 1, max_usd_per_run: 0.1, max_tool_calls: 1 }
io: { input_schema: "x.json", output_schema: "y.json" }
governs:
  paths:
    - "src/agents/fake/**"
---
"""

DANGLING_SPEC = """\
---
id: ADR-900
title: Dangling glob demo
status: draft
version: 0.1.0
owner: "@tester"
date: 2026-08-17
governs:
  paths:
    - "src/does/not/exist/**"
---
"""

TIE_SPEC_A = """\
---
id: ADR-901
title: Tie A
status: draft
version: 0.1.0
owner: "@tester"
date: 2026-08-17
governs:
  paths:
    - "src/agents/tied.py"
---
"""

TIE_SPEC_B = """\
---
id: ADR-902
title: Tie B
status: draft
version: 0.1.0
owner: "@tester"
date: 2026-08-17
governs:
  paths:
    - "src/agents/tied.py"
---
"""

EXTENDS_SPEC = """\
---
id: ADR-903
title: Extends the tie
status: draft
version: 0.1.0
owner: "@tester"
date: 2026-08-17
extends: ADR-901
governs:
  paths:
    - "src/agents/tied.py"
---
"""


def _init_repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "tester"], cwd=tmp_path, check=True)
    return tmp_path


def _commit_all(repo_root: Path) -> None:
    subprocess.run(["git", "add", "-A"], cwd=repo_root, check=True)


def test_build_index_resolves_longest_match(tmp_path: Path) -> None:
    repo_root = _init_repo(tmp_path)
    (repo_root / "specs").mkdir()
    (repo_root / "specs" / "CON-900.md").write_text(CON_SPEC)
    (repo_root / "specs" / "AGT-900.md").write_text(AGT_SPEC)
    agents_dir = repo_root / "src" / "agents" / "fake"
    agents_dir.mkdir(parents=True)
    (agents_dir / "node.py").write_text("# node\n")
    _commit_all(repo_root)

    index = build_index(repo_root / "specs", repo_root)

    assert index.owners["src/agents/fake/node.py"] == "AGT-900"
    assert resolve("src/agents/fake/node.py", index) == "AGT-900"


def test_build_index_flags_dangling_glob(tmp_path: Path) -> None:
    repo_root = _init_repo(tmp_path)
    (repo_root / "specs").mkdir()
    (repo_root / "specs" / "ADR-900.md").write_text(DANGLING_SPEC)
    (repo_root / "README.md").write_text("hi\n")
    _commit_all(repo_root)

    index = build_index(repo_root / "specs", repo_root)

    assert any(d.kind == "dangling" and "ADR-900" in d.message for d in index.diagnostics)


def test_build_index_flags_ambiguous_ownership(tmp_path: Path) -> None:
    repo_root = _init_repo(tmp_path)
    (repo_root / "specs").mkdir()
    (repo_root / "specs" / "ADR-901.md").write_text(TIE_SPEC_A)
    (repo_root / "specs" / "ADR-902.md").write_text(TIE_SPEC_B)
    agents_dir = repo_root / "src" / "agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "tied.py").write_text("# tied\n")
    _commit_all(repo_root)

    index = build_index(repo_root / "specs", repo_root)

    assert any(d.kind == "ambiguous" and "tied.py" in d.message for d in index.diagnostics)
    assert "src/agents/tied.py" not in index.owners


def test_ambiguity_resolved_by_extends(tmp_path: Path) -> None:
    repo_root = _init_repo(tmp_path)
    (repo_root / "specs").mkdir()
    (repo_root / "specs" / "ADR-901.md").write_text(TIE_SPEC_A)
    (repo_root / "specs" / "ADR-903.md").write_text(EXTENDS_SPEC)
    agents_dir = repo_root / "src" / "agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "tied.py").write_text("# tied\n")
    _commit_all(repo_root)

    index = build_index(repo_root / "specs", repo_root)

    assert index.owners["src/agents/tied.py"] == "ADR-903"
    assert not any(d.kind == "ambiguous" for d in index.diagnostics)


def test_build_index_flags_orphan_file(tmp_path: Path) -> None:
    repo_root = _init_repo(tmp_path)
    (repo_root / "specs").mkdir()
    (repo_root / "specs" / "AGT-900.md").write_text(AGT_SPEC)
    other_dir = repo_root / "src" / "unrelated"
    other_dir.mkdir(parents=True)
    (other_dir / "thing.py").write_text("# unowned\n")
    _commit_all(repo_root)

    index = build_index(repo_root / "specs", repo_root)

    assert any(
        d.kind == "orphan" and "src/unrelated/thing.py" in d.message for d in index.diagnostics
    )


def test_resolve_returns_spec_id_or_none(tmp_path: Path) -> None:
    repo_root = _init_repo(tmp_path)
    (repo_root / "specs").mkdir()
    (repo_root / "specs" / "AGT-900.md").write_text(AGT_SPEC)
    agents_dir = repo_root / "src" / "agents" / "fake"
    agents_dir.mkdir(parents=True)
    (agents_dir / "node.py").write_text("# node\n")
    _commit_all(repo_root)

    index = build_index(repo_root / "specs", repo_root)

    assert resolve("src/agents/fake/node.py", index) == "AGT-900"
    assert resolve("src/agents/other/thing.py", index) is None


def test_resolve_matches_untracked_path_via_pattern_fallback(tmp_path: Path) -> None:
    repo_root = _init_repo(tmp_path)
    (repo_root / "specs").mkdir()
    (repo_root / "specs" / "AGT-900.md").write_text(AGT_SPEC)
    _commit_all(repo_root)

    index = build_index(repo_root / "specs", repo_root)

    assert resolve("src/agents/fake/brand_new_file.py", index) == "AGT-900"


def test_repo_index_is_clean() -> None:
    index = build_index(REPO_ROOT / "specs", REPO_ROOT)

    assert index.diagnostics == [], "\n".join(str(d) for d in index.diagnostics)
