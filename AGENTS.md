# agent-forge — agent instructions

This is the **framework** repo (`agentcore` + spec templates + the copier
template). No real agent runs here — real projects are generated from this
repo via `copier copy gh:yourorg/agent-forge my-project` and depend on
`agentcore` as a pinned package. See `agentic-platform-plan.md` for the full
design; this file only states the rules that must never be skipped.

## The one rule

**A governed file cannot be edited without its spec resolved first.** Every
path under `src/`, `prompts/`, `tests/`, `configs/`, `deploy/` is owned by a
spec in `specs/` (see `CON-001` in `specs/constitution.md`). Before editing
such a file, find and read its governing spec. If none exists, create one
before writing code — don't scaffold implementation ahead of its spec.

## Spec lifecycle

`/specify` → `/clarify` → `/plan` → `/tasks` → `/implement` → `/verify` →
`/accept`. No implementation PR merges without an `approved` spec covering
the changed paths.

## Working in this repo

- `uv sync --frozen && uv run pytest` is the entire local setup story.
- `uv run` is the only sanctioned entrypoint — never call `python` or `pip`
  directly.
- Don't hand-edit `uv.lock`; run `uv lock` and commit the result.
- Spec kinds and what they govern: see `specs/constitution.md` §"Spec
  taxonomy" (mirrors the plan's §1.3).
- This repo's own CI is GitHub Actions only (`.github/workflows/`) — no
  portability shims for other CI hosts.

## Human-in-the-loop

Unattended/scheduled graphs must not use runtime `interrupt()` approval
gates — pre-approve at the spec level instead. `interrupt()` is reserved for
attended, CLI-driven runs (`forge resume <thread_id>`).

## Escalation

Any rule on this page that keeps getting violated should be promoted into a
hook (`.claude/settings.json`) or a CI gate, not repeated here.
