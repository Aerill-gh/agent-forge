# agent-forge

Framework repo for spec-driven, LangGraph-orchestrated, LangSmith-traced
agentic projects. See [agentic-platform-plan.md](agentic-platform-plan.md)
for the full design and [AGENTS.md](AGENTS.md) for the rules a coding agent
must follow in this repo.

**Status:** P3 (agent runtime) — P0-P2 (spec engine, binding layer, hooks,
nested `AGENTS.md`, `spec-workflow` skill) are complete; see git history
for that layer. P3 adds: layered `AppConfig` (`agentcore.config`), a
provider-agnostic `ModelRouter` (`agentcore.llm`, tiers from
`configs/models.yaml`, fallback chains via `init_chat_model`), a RAIL
prompt loader with `## Limits`-required linting (`agentcore.prompts`), an
`AGT-` spec -> compiled LangGraph agent factory (`agentcore.agents`), a
pure-Python `BudgetTracker` (`agentcore.budget`), and LangSmith env-var
wiring off an `OPS-` spec (`agentcore.observability`). All verified
against a fake/injected chat model in this repo's own tests — no real
agent runs here (per `CLAUDE.md`), so nothing here makes a live provider
call; that's the generated-project verification point, P8. `DS-`
enforcement (`GovernedClient`), MCP tooling, and multi-agent graph
builders are not built yet; those land in P4/P5.

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
