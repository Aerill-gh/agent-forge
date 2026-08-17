import subprocess
from pathlib import Path

from agentcore.specs.lint import spec_lint

REPO_ROOT = Path(__file__).resolve().parents[2]


def _init_repo(repo_root: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=repo_root, check=True)
    subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=repo_root, check=True)
    subprocess.run(["git", "config", "user.name", "tester"], cwd=repo_root, check=True)


def _commit_all(repo_root: Path) -> None:
    subprocess.run(["git", "add", "-A"], cwd=repo_root, check=True)


CLEAN_ADR = """\
---
id: ADR-997
title: Clean spec
status: approved
version: 1.0.0
owner: "@tester"
date: 2026-08-17
governs:
  paths:
    - "tests/unit/test_specs_lint.py"
acceptance:
  - id: AC-1
    then: "does the thing"
    verified_by: tests/unit/test_specs_lint.py::test_lint_passes_clean_spec
---

# ADR-997 — Clean spec
"""

DIRTY_ADR = """\
---
id: ADR-996
title: Dirty spec
status: approved
version: 1.0.0
owner: "@tester"
date: 2026-08-17
governs:
  paths:
    - "tests/unit/test_specs_lint.py"
acceptance:
  - id: AC-1
    then: "does the thing"
    verified_by: tests/unit/test_specs_lint.py::test_does_not_exist_anywhere
---

# ADR-996 — Dirty spec
"""


def test_lint_flags_missing_verifying_test(tmp_path: Path) -> None:
    repo_root = tmp_path
    _init_repo(repo_root)
    specs_dir = repo_root / "specs"
    specs_dir.mkdir()
    (specs_dir / "ADR-996-dirty.md").write_text(DIRTY_ADR)
    (repo_root / "tests" / "unit").mkdir(parents=True)
    (repo_root / "tests" / "unit" / "test_specs_lint.py").write_text("def test_other(): pass\n")
    _commit_all(repo_root)

    failures = spec_lint(specs_dir, repo_root)

    assert len(failures) == 1
    assert "AC-1" in failures[0].message
    assert "does not resolve" in failures[0].message


def test_lint_passes_clean_spec(tmp_path: Path) -> None:
    repo_root = tmp_path
    _init_repo(repo_root)
    specs_dir = repo_root / "specs"
    specs_dir.mkdir()
    (specs_dir / "ADR-997-clean.md").write_text(CLEAN_ADR)
    (repo_root / "tests" / "unit").mkdir(parents=True)
    (repo_root / "tests" / "unit" / "test_specs_lint.py").write_text(
        "def test_lint_passes_clean_spec(): pass\n"
    )
    _commit_all(repo_root)

    failures = spec_lint(specs_dir, repo_root)

    assert failures == []


def test_repo_specs_are_lint_clean() -> None:
    failures = spec_lint(REPO_ROOT / "specs", REPO_ROOT)

    assert failures == [], "\n".join(str(f) for f in failures)


def test_spec_guard_workflow_runs_lint() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "spec-guard.yml").read_text()

    assert "forge spec lint" in workflow
    assert "pull_request" in workflow
