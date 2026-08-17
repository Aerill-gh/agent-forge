"""`resolve(target, index)` — the one resolver function, per plan §4.2.

Checks the precomputed `owners` cache first (fast path, matches the
plan's "hooks resolve offline in milliseconds" off a committed index);
falls back to live pattern matching so a path that isn't tracked by git
yet — e.g. a file about to be created — still resolves correctly.
"""

from __future__ import annotations

from pathlib import Path

from agentcore.specs.index import SpecIndex, owner_for_path


def resolve(target: str, index: SpecIndex) -> str | None:
    """Return the spec id governing `target`, or None if unowned."""
    normalized = Path(target).as_posix()
    cached = index.owners.get(normalized)
    if cached is not None:
        return cached
    owner, _diagnostic = owner_for_path(normalized, index.patterns, index.extends)
    return owner
