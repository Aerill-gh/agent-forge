---
id: ADR-003
title: Nested AGENTS.md generator and the spec-workflow skill
status: approved
version: 1.0.0
owner: "@vachik"
date: 2026-08-17
extends: ADR-002
governs:
  paths:
    - "src/agentcore/specs/agents_md.py"
    - "tests/unit/test_specs_agents_md.py"
    - ".claude/skills/spec-workflow/**"
acceptance:
  - id: AC-1
    given: "the repo's own governs index"
    then: "sync_agents_md() writes one AGENTS.md per governed-root directory that owns at least one file, listing each owning spec and the file->spec mapping"
    verified_by: tests/unit/test_specs_agents_md.py::test_sync_writes_one_agents_md_per_governed_directory
  - id: AC-2
    given: "a directory whose files are owned by more than one spec"
    then: "the generated AGENTS.md lists every owning spec, not just one"
    verified_by: tests/unit/test_specs_agents_md.py::test_sync_lists_all_owning_specs_for_mixed_directory
  - id: AC-3
    given: "an on-disk nested AGENTS.md that no longer matches what sync_agents_md would generate"
    then: "check_agents_md() reports it as stale"
    verified_by: tests/unit/test_specs_agents_md.py::test_check_flags_stale_agents_md
  - id: AC-4
    given: "the repo's own committed nested AGENTS.md files, freshly regenerated"
    then: "check_agents_md() reports zero stale files"
    verified_by: tests/unit/test_specs_agents_md.py::test_repo_agents_md_is_in_sync
  - id: AC-5
    then: "the spec-workflow skill's frontmatter names the spec kinds and the src/prompts/tests/configs/deploy roots it should trigger on"
    verified_by: tests/unit/test_specs_agents_md.py::test_spec_workflow_skill_frontmatter_names_governed_roots
---

# ADR-003 — Nested AGENTS.md generator and the spec-workflow skill

## Context

ADR-002 shipped the hook (layer 3) and CI gate (layer 2) halves of the
plan's §4.3 authoring-time binding list. Two items remain: **nested
`AGENTS.md`** (point 3 — cross-tool fallback for editors without Claude
Code's hook support) and the **`spec-workflow` skill** (point 4 —
auto-triggers on agent/graph/tool/eval work). Both are documentation
surfaces, not enforcement, but per the plan's enforcement ladder (§2) they
raise the *ergonomics* floor so compliance is the easy path — especially
for a tool that never fires `PreToolUse`.

## Decision

- **`agents_md.py`** — `sync_agents_md(specs_dir, repo_root, dry_run=False)`
  groups `build_index()`'s resolved owners by directory (restricted to the
  governed roots — `src/`, `prompts/`, `tests/`, `configs/`, `deploy/`),
  and for every directory that owns at least one file, generates an
  `AGENTS.md` listing each owning spec (id, title, status, file path) and
  the per-file `filename -> spec_id` mapping. Mixed-ownership directories
  (common — see ADR-001's v1.1.0 amendment) list every owning spec, they
  are not skipped or forced into a single answer. `dry_run=True` returns
  `(path, content)` pairs without writing, which `check_agents_md()` uses
  to diff against what is actually on disk and report **stale** nested
  files — the mechanism that keeps this from decaying into exactly the
  kind of unenforced doc the plan's layer 6 (`AGENTS.md` itself) warns
  against.
- **CLI** — `forge spec sync-agents-md` writes the generated files;
  `spec_lint` calls `check_agents_md()` and fails on any stale file, so a
  spec/ownership change that doesn't regenerate the nested files fails CI
  (layer 2), same enforcement shape as the rest of P1/P2.
- **`spec-workflow` skill** — `.claude/skills/spec-workflow/SKILL.md`
  documents the `/specify -> /clarify -> /plan -> /tasks -> /implement ->
  /verify -> /accept` lifecycle from `CON-001` §3, points at
  `specs/templates/*.md` for the right template per kind, and at `forge
  spec for/lint/index` for checking existing coverage before writing a new
  spec. Its frontmatter description names the spec kinds and governed
  roots explicitly so it auto-triggers on the task shapes the plan's §4.3
  point 4 calls out (agent/graph/tool/eval work, or any edit under a
  governed root with no resolved spec).

## Alternatives considered

- **Hand-maintain nested `AGENTS.md` files.** Rejected: drift-prone by
  construction — exactly the failure mode `CON-001` §1 says the binding
  has to not be. Generating them from the same index the hook and CLI use
  means there is one source of truth, not three.
- **Skip the stale-check and just regenerate on demand.** Rejected: without
  a CI-enforced check, a spec's `governs:` block could change (new file
  added, ownership reassigned) without anyone remembering to re-run
  `forge spec sync-agents-md`, and the nested files would silently lie —
  the same drift risk as hand-maintaining them, one layer removed.

## Consequences

- Nested `AGENTS.md` files are generated artifacts now, not authored
  content — `git diff` on one after a spec change is a review signal that
  ownership moved, not accidental content.
- `spec_lint` now has four checks (dangling, ambiguous, orphan, stale nested
  `AGENTS.md`), all sourced from the same `build_index()` call — no
  second index or config for this feature.
- The skill is documentation + workflow guidance only; it does not enforce
  anything by itself (plan's enforcement ladder layer 5, "raises the
  trigger rate," not binding) — that's still the hook and CI gate.
