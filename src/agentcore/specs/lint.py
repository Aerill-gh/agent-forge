"""spec_lint: walk specs/, validate each, and check acceptance criteria
resolve to a real verifying test or eval, per ADR-001.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from agentcore.specs.agents_md import check_agents_md
from agentcore.specs.index import build_index
from agentcore.specs.loader import SpecParseError, SpecValidationError, load_spec
from agentcore.specs.models import SpecBase

_TEST_REF_PATTERN = re.compile(r"^(?P<path>[^:]+\.py)::(?P<func>\w+)$")
_EVAL_REF_PATTERN = re.compile(r"^eval:(?P<eval_id>EVL-[0-9]{3,})$")


@dataclass(frozen=True)
class LintFailure:
    spec_path: Path
    message: str

    def __str__(self) -> str:
        return f"{self.spec_path}: {self.message}"


def verified_by_resolves(verified_by: str, repo_root: Path) -> bool:
    test_match = _TEST_REF_PATTERN.match(verified_by)
    if test_match:
        test_path = repo_root / test_match.group("path")
        if not test_path.is_file():
            return False
        func_name = test_match.group("func")
        pattern = rf"^\s*(?:async\s+)?def {re.escape(func_name)}\s*\("
        return re.search(pattern, test_path.read_text(), re.M) is not None

    eval_match = _EVAL_REF_PATTERN.match(verified_by)
    if eval_match:
        eval_id = eval_match.group("eval_id")
        return any((repo_root / "specs" / "evals").glob(f"{eval_id}-*.md")) or any(
            (repo_root / "specs" / "evals").glob(f"{eval_id}.md")
        )

    return False


def lint_spec_file(path: Path, repo_root: Path) -> list[LintFailure]:
    """Lint a single spec file. Returns an empty list if it is clean."""
    failures: list[LintFailure] = []

    try:
        spec: SpecBase = load_spec(path)
    except (SpecParseError, SpecValidationError) as exc:
        return [LintFailure(path, str(exc))]

    for criterion in spec.acceptance:
        if not verified_by_resolves(criterion.verified_by, repo_root):
            failures.append(
                LintFailure(
                    path,
                    f"acceptance {criterion.id!r} verified_by={criterion.verified_by!r} "
                    "does not resolve to an existing test function or eval spec",
                )
            )

    return failures


def spec_lint(specs_dir: str | Path, repo_root: str | Path | None = None) -> list[LintFailure]:
    """Lint every spec file under specs_dir. Returns all failures found."""
    specs_dir = Path(specs_dir)
    root = Path(repo_root) if repo_root is not None else specs_dir.parent

    failures: list[LintFailure] = []
    for path in sorted(specs_dir.rglob("*.md")):
        if path.name.startswith("_") or "templates" in path.parts:
            continue
        failures.extend(lint_spec_file(path, root))

    index = build_index(specs_dir, root)
    failures.extend(LintFailure(specs_dir, str(diagnostic)) for diagnostic in index.diagnostics)

    for stale in check_agents_md(specs_dir, root):
        failures.append(
            LintFailure(
                stale.path,
                f"nested AGENTS.md is {stale.reason} — run `forge spec sync-agents-md`",
            )
        )

    return failures
