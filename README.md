# agent-forge

Framework repo for spec-driven, LangGraph-orchestrated, LangSmith-traced
agentic projects. See [agentic-platform-plan.md](agentic-platform-plan.md)
for the full design and [AGENTS.md](AGENTS.md) for the rules a coding agent
must follow in this repo.

**Status:** P2 (binding layer) complete — UV workspace, skeleton, CI,
constitution, spec templates, a Pydantic-backed spec loader + `spec_lint`
gate, a `governs:` ownership index (`forge spec for`,
orphan/ambiguity/dangling checks folded into `spec_lint`), a local
`PreToolUse` hook (`scripts/hooks/resolve_spec.py`, wired in
`.claude/settings.json`) that blocks edits to files no spec governs,
generated nested `AGENTS.md` files kept in sync by `spec_lint`
(`forge spec sync-agents-md`), and the `spec-workflow` skill are all in
place. The agent runtime, `GovernedClient`, and multi-agent graphs are not
built yet; those land in P3+.

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
