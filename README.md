# agent-forge

Framework repo for spec-driven, LangGraph-orchestrated, LangSmith-traced
agentic projects. See [agentic-platform-plan.md](agentic-platform-plan.md)
for the full design and [AGENTS.md](AGENTS.md) for the rules a coding agent
must follow in this repo.

**Status:** P0 (foundations) — UV workspace, skeleton, CI, constitution and
spec templates are in place. No real spec engine, agent runtime, or MCP
governance yet; those land in P1+.

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
