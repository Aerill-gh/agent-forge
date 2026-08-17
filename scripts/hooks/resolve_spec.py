#!/usr/bin/env python3
"""PreToolUse hook (Edit|Write|MultiEdit), per ADR-002.

Blocks (exit 2) an edit to a file under a governed root that no spec
governs. Allows (exit 0) an edit to a file a spec governs, printing that
spec's id/status/acceptance criteria to stdout. Silently allows (exit 0)
anything outside the governed roots — untouched by CON-001's rule.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from agentcore.specs.index import GOVERNED_ROOTS, build_index  # noqa: E402
from agentcore.specs.loader import load_spec  # noqa: E402
from agentcore.specs.resolve import resolve  # noqa: E402


def _repo_root(payload: dict[str, object]) -> Path:
    cwd = payload.get("cwd")
    if isinstance(cwd, str):
        return Path(cwd)
    return Path(__file__).resolve().parents[2]


def _target_path(payload: dict[str, object]) -> str | None:
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return None
    file_path = tool_input.get("file_path")
    return file_path if isinstance(file_path, str) else None


def main() -> int:
    payload = json.loads(sys.stdin.read() or "{}")
    target = _target_path(payload)
    if target is None:
        return 0

    root = _repo_root(payload)
    try:
        rel_target = Path(target).resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return 0  # target outside the repo — not this hook's concern

    if rel_target.split("/", 1)[0] not in GOVERNED_ROOTS:
        return 0

    index = build_index(root / "specs", root)
    spec_id = resolve(rel_target, index)

    if spec_id is None:
        print(
            f"no spec governs {rel_target!r}. Create one first: "
            "run /specify, then /clarify -> /plan -> /tasks -> /implement (see CLAUDE.md).",
            file=sys.stderr,
        )
        return 2

    matches = list((root / "specs").rglob(f"{spec_id}*.md"))
    matches = [m for m in matches if "templates" not in m.parts]
    model = load_spec(matches[0])
    print(f"governed by {model.id} ({model.title!r}, status={model.status})")
    for criterion in model.acceptance:
        print(f"  {criterion.id}: {criterion.then}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
