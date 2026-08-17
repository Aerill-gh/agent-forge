import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK = REPO_ROOT / "scripts" / "hooks" / "resolve_spec.py"


def _run_hook(file_path: str) -> subprocess.CompletedProcess[str]:
    payload = json.dumps(
        {
            "cwd": str(REPO_ROOT),
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {"file_path": str(REPO_ROOT / file_path)},
        }
    )
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=payload,
        capture_output=True,
        text=True,
    )


def test_hook_blocks_unowned_path() -> None:
    result = _run_hook("src/totally/unowned/module.py")

    assert result.returncode == 2
    assert "no spec governs" in result.stderr


def test_hook_allows_owned_path() -> None:
    result = _run_hook("src/agentcore/specs/index.py")

    assert result.returncode == 0
    assert "ADR-002" in result.stdout


def test_hook_ignores_ungoverned_root() -> None:
    result = _run_hook("README.md")

    assert result.returncode == 0
    assert result.stdout == ""
