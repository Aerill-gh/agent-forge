---
id: CON-001
title: agent-forge Constitution
status: approved
version: 1.0.0
owner: "@vachik"
governs:
  paths:
    - "**"
---

# CON-001 — Constitution

Non-negotiable rules for this repository and every project generated from
it. One constitution per repo. Anything here overrides a lower-priority
spec, `AGENTS.md`, or a skill.

## 1. Central guarantee

Nothing in a generated project can be edited or executed without its
governing spec being resolved first. Touch a file → its spec is loaded.
Query a data source → its spec is enforced. That binding is mechanical
(loaders, resolvers, `GovernedClient`, CI gates), not advisory.

## 2. Spec taxonomy

| Prefix | Kind | Governs |
|---|---|---|
| `CON-` | Constitution | Non-negotiable project rules (one per repo) |
| `AGT-` | Agent spec | One agent: role, model tier, tools, I/O schema, budget, acceptance criteria |
| `GRP-` | Graph spec | Multi-agent topology, handoffs, termination, escalation |
| `TOOL-` | Tool / MCP spec | A tool or MCP server contract: scopes, rate limits, data classification |
| `DS-` | Data source spec | A database, table set, API, file store or index: schema, semantics, PII class, allowed operations, freshness |
| `EVL-` | Eval spec | Dataset, evaluators, thresholds, regression policy |
| `OPS-` | Ops spec | Deployment target, LangSmith target, provider(s), environments, SLOs, cost budgets |
| `ADR-` | Decision record | Architecture decisions with alternatives and consequences |

## 3. Spec lifecycle

`/specify` → `/clarify` → `/plan` → `/tasks` → `/implement` → `/verify` →
`/accept`. No implementation PR merges without an `approved` spec covering
the changed paths. An approved spec whose acceptance criteria change
without a version bump fails the build.

## 4. Human-in-the-loop (locked, see plan §12 decision 6)

**CLI only.** `forge resume <thread_id>` resumes paused background runs.
Unattended/scheduled graphs must **not** use runtime `interrupt()` approval
gates — pre-approve the behavior at the spec level instead. `interrupt()`
is reserved for attended, CLI-driven sessions (e.g. the `/plan` approval
step of the spec workflow itself).

## 5. Ownership granularity (plan §12 decision 7)

Fine-grained `governs:` per agent/prompt file. Coarse per-module ownership
is acceptable for shared `agentcore` utilities that no single feature spec
owns.

## 6. Enforcement ladder

Six layers, ordered by how much they actually bind — design the weak ones
for ergonomics, rely on the strong ones. See `agentic-platform-plan.md` §2
for the full table. Any rule in `AGENTS.md` that is repeatedly ignored gets
promoted into a stronger layer (a hook or a CI gate).

## 7. Locked configuration

Deployment target, model providers, and LangSmith target are **generation-time
choices**, made once via copier prompts and recorded in each generated
project's `OPS-001` spec — never re-litigated ad hoc per PR. CI host is
GitHub only; no portability layer for other CI hosts. See
`agentic-platform-plan.md` §12 for the full locked-decision table.
