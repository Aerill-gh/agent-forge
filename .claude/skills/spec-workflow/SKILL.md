---
name: spec-workflow
description: >
  Use before writing or editing any file under src/, prompts/, tests/,
  configs/, or deploy/ that has no governing spec yet, or when creating an
  AGT- (agent), GRP- (graph), TOOL- (MCP tool), DS- (data source), EVL-
  (eval), OPS- (ops), or ADR- (decision record) spec. Triggers on "add an
  agent", "new tool", "wire up a data source", "write an eval", "spec
  this", or a PreToolUse hook block naming a path with no resolved spec.
---

# spec-workflow

Per `CON-001` (`specs/constitution.md`) §1: a governed file cannot be
edited without its spec resolved first. This skill is the walkthrough for
resolving one — either finding the spec that already governs a path, or
creating a new one before touching code.

## 1. Check for an existing spec first

```bash
uv run forge spec for <path>
```

- Prints the governing spec id and exits 0 → read that spec
  (`uv run forge spec show <id>`), then edit. Don't create a new one.
- Exits 1 (`no spec governs <path>`) → no spec covers this path yet.
  Continue to step 2.

## 2. Pick the right template

| What you're building | Kind | Template |
|---|---|---|
| An agent (role, model tier, tools, budget) | `AGT-` | `specs/templates/agent.md` |
| A multi-agent topology / handoffs | `GRP-` | `specs/templates/graph.md` |
| An MCP tool / tool contract | `TOOL-` | `specs/templates/tool.md` |
| A database, table set, API, index | `DS-` | `specs/templates/data_source.md` |
| An eval dataset / evaluator / threshold | `EVL-` | `specs/templates/eval.md` |
| Deploy target, providers, SLOs, budgets | `OPS-` | `specs/templates/ops.md` |
| An architecture decision, or framework-internal code with no better fit | `ADR-` | `specs/templates/adr.md` |

Copy the template into the matching `specs/<kind>/` directory, named
`<ID>-<slug>.md` (e.g. `specs/agents/AGT-014-risk-extractor.md`). Pick the
next unused id for that prefix — `ls specs/<kind>/` to check what's taken.

## 3. Fill it in — the lifecycle

`/specify -> /clarify -> /plan -> /tasks -> /implement -> /verify ->
/accept`, per `CON-001` §3:

1. **`/specify`** — role/purpose, `governs.paths` (the exact files this
   spec will own — this is what `forge spec for` resolves against),
   `status: draft`.
2. **`/clarify`** — resolve any open questions before committing to a
   design (budget numbers, model tier, tool allowlist).
3. **`/plan` + `/tasks`** — break the acceptance criteria into concrete
   `given/then/verified_by` entries. Every `verified_by` must point at a
   test that will actually exist (`path/to/test.py::test_name`) or an eval
   spec (`eval:EVL-NNN`) — `spec_lint` fails the build otherwise (see
   ADR-001).
4. **`/implement`** — write the code and the tests `verified_by` names.
5. **`/verify`** — run `uv run forge spec lint specs` and `uv run pytest`.
   Both must pass before requesting review.
6. **`/accept`** — flip `status: draft` -> `approved` only once every
   acceptance criterion's test passes. `CON-001` §3: no implementation PR
   merges without an approved spec covering the changed paths.

## 4. Regenerate the ownership index

Any `governs.paths` change (new spec, edited pattern, reassigned
ownership) needs:

```bash
uv run forge spec sync-agents-md
```

`spec_lint` fails CI if a nested `AGENTS.md` is stale relative to the
current index (ADR-003) — this is what keeps them from silently drifting.

## Notes

- `CON-` (constitution) specs never resolve `forge spec for` on their own
  — they state repo-wide rules, not per-file ownership (ADR-002). If
  `forge spec for` returns nothing for a path under a governed root, that
  path genuinely has no feature/framework spec yet, even if `CON-001`
  itself "matches" everything.
- Coarse, module-level `governs.paths` (e.g. `src/agentcore/**`) are
  acceptable for shared framework utilities that no single feature spec
  owns — see `CON-001` §5. Prefer fine-grained ownership for anything
  agent/tool/graph-specific.
- Unattended/scheduled graphs must not use runtime `interrupt()` approval
  gates — pre-approve at the spec level instead (`CON-001` §4). Don't
  design an `AGT-`/`GRP-` spec around a runtime approval step unless the
  run is explicitly CLI-driven and attended.
