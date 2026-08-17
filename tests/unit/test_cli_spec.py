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
