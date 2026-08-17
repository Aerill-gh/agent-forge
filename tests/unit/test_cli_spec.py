import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", "from agentcore.cli import main; main()", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )


def test_cli_spec_lint_clean_repo() -> None:
    result = _run("spec", "lint", "specs")

    assert result.returncode == 0
    assert "clean" in result.stdout


def test_cli_spec_show_known_id() -> None:
    result = _run("spec", "show", "ADR-001")

    assert result.returncode == 0
    assert '"id": "ADR-001"' in result.stdout


def test_cli_spec_show_unknown_id() -> None:
    result = _run("spec", "show", "ADR-000")

    assert result.returncode == 1
    assert "no spec file found" in result.stderr


def test_cli_spec_for_owned_path() -> None:
    result = _run("spec", "for", "src/agentcore/specs/index.py")

    assert result.returncode == 0
    assert result.stdout.strip() == "ADR-002"


def test_cli_spec_for_unowned_path() -> None:
    result = _run("spec", "for", "src/totally/unowned/module.py")

    assert result.returncode == 1
    assert "no spec governs" in result.stderr


def test_cli_spec_sync_agents_md_is_idempotent_on_repo() -> None:
    result = _run("spec", "sync-agents-md")

    assert result.returncode == 0
    assert "src/agentcore/specs/AGENTS.md" in result.stdout
