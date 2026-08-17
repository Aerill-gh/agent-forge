---
id: ADR-001
title: Spec engine — Pydantic models, loader, and lint gate
status: approved
version: 1.0.0
owner: "@vachik"
date: 2026-08-17
governs:
  paths:
    - "src/agentcore/specs/**"
    - "tests/unit/test_specs_*.py"
    - ".github/workflows/spec-guard.yml"
acceptance:
  - id: AC-1
    given: "a spec file with valid frontmatter for its id prefix"
    then: "load_spec() returns a validated, kind-specific Pydantic model"
    verified_by: tests/unit/test_specs_loader.py::test_load_spec_valid
  - id: AC-2
    given: "a spec file whose frontmatter violates its kind's schema (e.g. bad id pattern, missing governs)"
    then: "load_spec() raises a SpecValidationError naming the offending field"
    verified_by: tests/unit/test_specs_loader.py::test_load_spec_invalid
  - id: AC-3
    given: "a spec directory containing a spec whose acceptance criteria reference a test that does not exist"
    then: "spec_lint() reports it as a failure (missing verifying test)"
    verified_by: tests/unit/test_specs_lint.py::test_lint_flags_missing_verifying_test
  - id: AC-4
    given: "a spec directory where every acceptance criterion resolves to an existing test or eval"
    then: "spec_lint() reports no failures for that spec"
    verified_by: tests/unit/test_specs_lint.py::test_lint_passes_clean_spec
  - id: AC-5
    then: "spec-guard.yml runs forge spec lint over specs/ on every PR"
    verified_by: tests/unit/test_specs_lint.py::test_spec_guard_workflow_runs_lint
  - id: AC-6
    given: "the repo's own specs/ directory, as committed"
    then: "spec_lint() reports zero failures"
    verified_by: tests/unit/test_specs_lint.py::test_repo_specs_are_lint_clean
---

# ADR-001 — Spec engine

## Context

P0 shipped spec templates and a placeholder JSON Schema
(`specs/schema/spec.schema.json`) that only checks frontmatter shape. There
is no code that loads a spec, no per-kind validation (an `AGT-` spec and a
`DS-` spec have different required fields), and nothing that checks a
spec's acceptance criteria actually resolve to a test. Per the plan (§11,
P1) and `CON-001` §1, the central guarantee — no governed file edits
without a resolved spec — is meaningless until specs are machine-loadable
and machine-checkable.

## Decision

Build `agentcore.specs` as the spec engine:

- **`models.py`** — a `SpecBase` Pydantic model matching the common
  frontmatter shape in `spec.schema.json`, plus one subclass per kind
  (`ConstitutionSpec`, `AgentSpec`, `GraphSpec`, `ToolSpec`,
  `DataSourceSpec`, `EvalSpec`, `OpsSpec`, `AdrSpec`) adding kind-specific
  required fields (e.g. `AgentSpec` requires `model_tier`, `budget`, `io`).
- **`loader.py`** — `load_spec(path) -> SpecBase` parses YAML frontmatter +
  Markdown body, dispatches to the right model by the `id` prefix, and
  raises `SpecValidationError` on any mismatch.
- **`lint.py`** — `spec_lint(specs_dir) -> list[LintFailure]` walks every
  spec, validates it via `load_spec`, and for each `acceptance` entry
  resolves `verified_by` (`path/to/test.py::test_name` or `eval:EVL-NNN`)
  against the actual test file/function or a known eval spec id. A spec
  with an acceptance criterion that resolves to nothing is a lint failure.
  This is the mechanism behind the P1 exit criterion: *a spec with no
  verifying test fails CI*.
- **`decorators.py`** — `@spec("AGT-014")` records a code object's owning
  spec id in a registry (`agentcore.specs.registry`) for the P2 binding
  layer to consume; P1 only needs the registry to exist and be inspectable,
  not enforced yet.
- **CLI** — `forge spec lint` runs `spec_lint` over `specs/` and exits
  non-zero on failure; `forge spec show <id>` prints the resolved model.
- **CI** — `.github/workflows/spec-guard.yml` runs `forge spec lint` on
  every PR touching `specs/**`.

## Alternatives considered

- **JSON Schema only, no Pydantic models.** Rejected: JSON Schema can
  express the common shape (already does, in P0) but per-kind conditional
  requirements and Python-side ergonomics (typed access in the loader,
  resolver, and future `GovernedClient`) are much harder to express and
  consume as raw JSON Schema than as Pydantic subclasses.
- **Enforce `verified_by` resolution via a git hook instead of CI.** Rejected
  for P1: a hook can be bypassed locally; CI is the layer that actually
  blocks a merge, per `CON-001` §6 (enforcement ladder — rely on the strong
  layers).

## Consequences

- Every spec kind now has a real, importable Python type — later phases
  (P2 binding, P3 runtime factory, P4 `GovernedClient`) build directly on
  `agentcore.specs.models` rather than re-parsing YAML.
- Adding a new spec kind means adding a model subclass and a lint rule, not
  editing a loose schema file by hand.
- This does not yet implement the `governs:` resolver (which file is
  governed by which spec) — that is explicitly P2 (binding layer) per the
  plan's milestone table, and is out of scope here.
