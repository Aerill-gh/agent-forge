---
id: ADR-002
title: Binding layer — governs index, resolver, and the PreToolUse gate
status: approved
version: 1.0.0
owner: "@vachik"
date: 2026-08-17
extends: ADR-001
governs:
  paths:
    - "src/agentcore/specs/index.py"
    - "src/agentcore/specs/resolve.py"
    - "scripts/hooks/**"
    - ".claude/settings.json"
    - "tests/unit/test_specs_index.py"
    - "tests/unit/test_hooks_*.py"
acceptance:
  - id: AC-1
    given: "every spec under specs/ with a governs.paths glob"
    then: "build_index() compiles a SpecIndex mapping each matched real path to its owning spec id, most-specific pattern wins"
    verified_by: tests/unit/test_specs_index.py::test_build_index_resolves_longest_match
  - id: AC-2
    given: "a spec whose governs.paths glob matches zero real files"
    then: "build_index() reports it as a dangling-glob diagnostic"
    verified_by: tests/unit/test_specs_index.py::test_build_index_flags_dangling_glob
  - id: AC-3
    given: "two specs claiming the same most-specific path with no extends relationship between them"
    then: "build_index() reports it as an ambiguous-ownership diagnostic"
    verified_by: tests/unit/test_specs_index.py::test_build_index_flags_ambiguous_ownership
  - id: AC-4
    given: "a file under a governed root (src/, prompts/, tests/, configs/, deploy/) that no spec's governs.paths matches"
    then: "build_index() reports it as an orphan-file diagnostic"
    verified_by: tests/unit/test_specs_index.py::test_build_index_flags_orphan_file
  - id: AC-5
    then: "resolve(target, index) returns the owning spec id for a path, or None if no spec governs it"
    verified_by: tests/unit/test_specs_index.py::test_resolve_returns_spec_id_or_none
  - id: AC-6
    given: "the repo's own specs/ directory and tracked files, as committed"
    then: "build_index() reports zero diagnostics (no dangling globs, no ambiguity, no orphans under governed roots)"
    verified_by: tests/unit/test_specs_index.py::test_repo_index_is_clean
  - id: AC-7
    given: "scripts/hooks/resolve_spec.py invoked with a target path under a governed root that no spec claims"
    then: "it exits 2 and writes a next-step message to stderr"
    verified_by: tests/unit/test_hooks_resolve_spec.py::test_hook_blocks_unowned_path
  - id: AC-8
    given: "scripts/hooks/resolve_spec.py invoked with a target path a spec governs"
    then: "it exits 0 and prints the governing spec id, status, and acceptance criteria to stdout"
    verified_by: tests/unit/test_hooks_resolve_spec.py::test_hook_allows_owned_path
---

# ADR-002 — Binding layer

## Context

ADR-001 made specs loadable and put a lint gate behind CI (layer 2 of the
enforcement ladder in the plan's §2). That only catches drift at PR time.
The plan's §4 calls for the stronger, faster layers: a compiled ownership
index so "which spec governs this file" is a lookup, not a search, and a
local hook (layer 3) that blocks an edit to a file no spec governs *before*
the edit happens — which is what `CON-001` §1's central guarantee actually
requires to be mechanical rather than advisory.

## Decision

- **`index.py`** — `build_index(specs_dir, repo_root) -> SpecIndex` walks
  every spec's `governs.paths` globs (fnmatch-style; `**` behaves as a
  free-form wildcard, matching across path separators — adequate for this
  repo's current glob shapes, revisit if a pattern needs literal-`/`
  semantics), matches them against `git ls-files`, and picks the owner of
  each matched path by **specificity** (count of non-`*` literal
  characters in the winning pattern — `CON-001`'s `"**"` has zero, so
  anything more specific wins). It also collects three diagnostics:
  **dangling** (a glob matching no tracked file), **ambiguous** (two specs
  tie for most-specific on the same path with no `extends` relationship —
  `extends` is a new optional field on `SpecBase`, naming another spec id
  a spec specializes), and **orphan** (a tracked file under a governed
  root — `src/`, `prompts/`, `tests/`, `configs/`, `deploy/`, per
  `CLAUDE.md` — matched by no spec). `spec_lint` folds all three in.
- **`resolve.py`** — `resolve(target, index) -> str | None`, the one
  resolver function the plan's §4.2 calls for. `forge spec for <path>` is
  the CLI face of it.
- **`scripts/hooks/resolve_spec.py`** — a `PreToolUse` hook for
  `Edit|Write|MultiEdit`. Reads the Claude Code hook JSON from stdin,
  extracts `tool_input.file_path`, resolves it against a freshly built
  index. Unowned (under a governed root) → exit 2, message on stderr
  naming the path and pointing at `/specify` (blocks the edit, per the
  hook contract: exit 2 stops the tool call and feeds stderr back).
  Owned → exit 0, spec id/status/acceptance printed on stdout. Wired into
  `.claude/settings.json` (committed, so it ships with the clone, per the
  plan's §4.3 point 1).

## Alternatives considered

- **Skip the index, resolve by re-globbing on every hook invocation.**
  Rejected: the plan explicitly calls for a compiled, committed
  `.spec-index.json` so resolution is offline and millisecond-fast;
  re-globbing every keystroke-adjacent hook call against every spec file
  doesn't hit that bar once the spec count grows. (P2 ships `build_index`
  as the compiler; wiring `forge spec index` to write the committed JSON
  artifact and having the hook load it instead of rebuilding is a
  same-shaped follow-up, not deferred on principle — noted under
  Consequences.)
- **Use `interrupt()`-style runtime blocking instead of a hook.** Rejected
  outright: `CON-001` §4 reserves `interrupt()` for attended, CLI-driven
  runs, and this is an authoring-time gate, not a graph runtime concern.

## Consequences

- `spec_lint` now enforces three of the four invariants the plan's §4.1
  lists (no orphans, no ambiguity, no dangling); "longest-match wins" is
  the resolver's core behavior, not a separate check.
- The hook only covers Claude Code (`PreToolUse`); nested `AGENTS.md` files
  (cross-tool fallback, plan §4.3 point 3) and the `spec-workflow` skill
  (point 4) are not part of this ADR's scope and remain open P2 work.
- `build_index` recomputes from `specs/` + `git ls-files` on every call
  rather than reading a committed `.spec-index.json`; wiring `forge spec
  index` to persist that artifact (so the hook doesn't re-walk `git
  ls-files` on every edit) is the natural next increment, not done here.
- The hook's stdin/stdout contract is implemented against the documented
  `PreToolUse` shape (`tool_input.file_path`, exit-code semantics); it is
  exercised by tests that invoke the script directly with a crafted stdin
  payload, not by an actual Claude Code session, since there is no harness
  to drive that end-to-end in CI.
