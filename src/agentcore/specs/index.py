"""Compile `governs:` blocks into an ownership index, per ADR-002.

`build_index` walks every spec's `governs.paths` globs against the repo's
tracked files and resolves, per path, which spec owns it (longest/most
specific pattern wins), collecting three diagnostics along the way:
dangling globs, ambiguous ownership, and orphan files under a governed
root (`src/`, `prompts/`, `tests/`, `configs/`, `deploy/`).

Resolution also works for paths that are *not yet* tracked by git (a file
about to be created) — `owners` is a fast-path cache over tracked files,
but `patterns` retains every (spec_id, pattern, specificity) triple so a
brand-new path can still be matched directly against the same glob rules.
"""

from __future__ import annotations

import fnmatch
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from agentcore.specs.loader import SpecParseError, SpecValidationError, load_spec
from agentcore.specs.models import SpecBase

GOVERNED_ROOTS = ("src", "prompts", "tests", "configs", "deploy")


@dataclass(frozen=True)
class Diagnostic:
    kind: str  # "dangling" | "ambiguous" | "orphan"
    message: str

    def __str__(self) -> str:
        return f"{self.kind}: {self.message}"


@dataclass(frozen=True)
class SpecIndex:
    owners: dict[str, str] = field(default_factory=dict)
    patterns: list[tuple[str, str, int]] = field(
        default_factory=list
    )  # (spec_id, pattern, specificity)
    extends: dict[str, str | None] = field(default_factory=dict)  # spec_id -> extends
    diagnostics: list[Diagnostic] = field(default_factory=list)


def _specificity(pattern: str) -> int:
    return len(pattern.replace("*", ""))


def _matches(pattern: str, path: str) -> bool:
    return fnmatch.fnmatch(path, pattern.replace("**", "*"))


def _tracked_files(repo_root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def iter_spec_files(specs_dir: str | Path) -> list[Path]:
    specs_dir = Path(specs_dir)
    return sorted(
        p
        for p in specs_dir.rglob("*.md")
        if not p.name.startswith("_") and "templates" not in p.parts
    )


def load_specs(specs_dir: str | Path) -> dict[str, SpecBase]:
    """Load every spec under specs_dir, keyed by id. Skips unparseable files."""
    specs: dict[str, SpecBase] = {}
    for path in iter_spec_files(specs_dir):
        try:
            loaded = load_spec(path)
        except (SpecParseError, SpecValidationError):
            continue  # spec_lint's per-file pass reports parse/validation failures
        specs[loaded.id] = loaded
    return specs


def spec_file_path(specs_dir: str | Path, spec_id: str) -> Path | None:
    """Find the file path for a given spec id, or None if not found."""
    for path in iter_spec_files(specs_dir):
        try:
            if load_spec(path).id == spec_id:
                return path
        except (SpecParseError, SpecValidationError):
            continue
    return None


def owner_for_path(
    path: str, patterns: list[tuple[str, str, int]], extends: dict[str, str | None]
) -> tuple[str | None, Diagnostic | None]:
    """Resolve a single path against (spec_id, pattern, specificity) triples.

    Works for any path string, tracked by git or not — used both to build
    the per-file owners cache and as the fallback for untracked paths.

    `CON-` specs never claim ownership here even when their pattern
    matches: a constitution states repo-wide rules, it isn't a feature
    spec that resolves the "this file has a governing spec" gate — see
    ADR-002.
    """
    candidates = [
        (spec_id, specificity)
        for spec_id, pattern, specificity in patterns
        if not spec_id.startswith("CON-") and _matches(pattern, path)
    ]
    if not candidates:
        return None, None

    top = max(specificity for _, specificity in candidates)
    tied = {spec_id for spec_id, specificity in candidates if specificity == top}
    if len(tied) == 1:
        return next(iter(tied)), None

    extenders = [sid for sid in tied if extends.get(sid) in tied]
    if len(extenders) == 1:
        return extenders[0], None

    return None, Diagnostic(
        "ambiguous",
        f"{path!r} is claimed at equal specificity by {sorted(tied)} with no extends relationship",
    )


def build_index(specs_dir: str | Path, repo_root: str | Path | None = None) -> SpecIndex:
    specs_dir = Path(specs_dir)
    root = Path(repo_root) if repo_root is not None else specs_dir.parent

    specs = load_specs(specs_dir)
    tracked = _tracked_files(root)
    diagnostics: list[Diagnostic] = []

    patterns: list[tuple[str, str, int]] = []
    extends = {spec_id: model.extends for spec_id, model in specs.items()}
    for spec_id, model in specs.items():
        if model.governs is None:
            continue
        for pattern in model.governs.paths:
            patterns.append((spec_id, pattern, _specificity(pattern)))
            if not any(_matches(pattern, path) for path in tracked):
                diagnostics.append(
                    Diagnostic(
                        "dangling",
                        f"{spec_id} governs.paths pattern {pattern!r} matches no tracked file",
                    )
                )

    owners: dict[str, str] = {}
    for path in tracked:
        owner, ambiguity = owner_for_path(path, patterns, extends)
        if ambiguity is not None:
            diagnostics.append(ambiguity)
        elif owner is not None:
            owners[path] = owner

    for path in tracked:
        if path.split("/", 1)[0] not in GOVERNED_ROOTS:
            continue
        if Path(path).name in (".gitkeep", "AGENTS.md"):
            continue  # generated meta files (ADR-003), not feature code needing their own spec
        if path not in owners:
            diagnostics.append(
                Diagnostic("orphan", f"{path!r} is under a governed root but no spec governs it")
            )

    return SpecIndex(owners=owners, patterns=patterns, extends=extends, diagnostics=diagnostics)
