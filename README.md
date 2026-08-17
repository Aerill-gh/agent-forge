# agent-forge

Framework repo for spec-driven, LangGraph-orchestrated, LangSmith-traced
agentic projects. See [agentic-platform-plan.md](agentic-platform-plan.md)
for the full design and [AGENTS.md](AGENTS.md) for the rules a coding agent
must follow in this repo.

**Status:** P4 (data & MCP governance) — P0-P3 (spec engine, binding
layer, hooks, nested `AGENTS.md`, `spec-workflow` skill, agent runtime:
config, `ModelRouter`, RAIL prompts, agent factory, budget middleware,
LangSmith wiring) are complete; see git history for those layers. P4
adds: `GovernedClient` (`agentcore.mcp`) enforcing a `DS-` spec
in-process — rejects unallowlisted tables and explicitly-requested denied
columns, strips incidentally-present denied columns, blocks over-limit
queries, auto-injects the row limit, tags every result with
`ds_spec_id`/classification/freshness; `redact_for_trace()`, the
cloud-redaction rule keyed off an `OPS-` spec's `langsmith_target` and a
`DS-` spec's `classification`; `MCPManager` resolving an agent's requested
tools against a `TOOL-` spec registry (unapproved/unknown tools rejected);
and `servers/spec_server/` — a real MCP server (package `mcp`) exposing
the plan's 8-tool budget (`spec_for_target`, `spec_get`, `spec_search`,
`spec_create`, `next_task`, `bind_test`, `scaffold_agent`, `spec_lint`),
tested in-process via `call_tool()`. `forge mcp doctor` and multi-agent
graph builders are not built yet; those land in the rest of P4/P5.

## Setup

```bash
uv sync --frozen
uv run pytest
```

## Layout

- `specs/` — `CON-001` constitution, per-kind spec templates, JSON Schema.
- `src/agentcore/` — framework package (stub subpackages for now).
- `tests/` — unit / contract / integration / evals.
- `.github/workflows/ci.yml` — lint, typecheck, test on 3.12 and 3.13.

This repo is framework-only: no real agent runs here. Real projects are
generated via `copier copy gh:yourorg/agent-forge my-project` (copier
template itself lands in P8).
