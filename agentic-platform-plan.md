# Agentic Platform Template — Implementation Plan

**Working name:** `agent-forge` (rename freely)
**Purpose:** one reusable framework repository that every future agentic project is generated *from* — spec-driven, UV-managed, LangGraph-orchestrated, LangSmith-traced, CI/CD-complete. All configuration decisions below are locked; nothing is left open.

**Central guarantee:** nothing in a generated project can be edited or executed without its governing spec being resolved first. Touch a file → its spec is loaded. Query a data source → its spec is enforced. That binding is mechanical, not advisory.

---

## 0. Principles (inherited from the training deck)

| Deck lesson | How the repo enforces it |
|---|---|
| Route by task, don't default to the biggest model | `ModelRouter` with LIGHT / VERSATILE / REASONING tiers; tier declared in the agent spec, not hardcoded |
| Keep only relevant context | Sub-agent isolation: heavy reads run in a subgraph and return a bounded summary to the parent state |
| Use RAIL (Role, Action, Information, Limits) | Prompt templates are RAIL-structured files; linter fails on a missing `Limits` section |
| Plan before build | Spec → Plan → Tasks gates; no implementation PR without an approved spec |
| Scope and reuse tools | MCP allowlist per agent, least privilege, tool-count budget checked in CI |
| Cache-friendly ordering | Prompt assembly puts stable context first, volatile input last |
| Instructions are code | `AGENTS.md` thin, versioned, reviewed, size-linted; chronic violations get promoted into hooks |
| Define "done" before starting | Every spec carries machine-readable acceptance criteria that become tests and LangSmith evaluators |
| Retrieve, don't dump | Specs, schemas and data dictionaries are fetched on demand via MCP, never preloaded wholesale |

---

## 1. Key technical decisions

### 1.1 Orchestrator: **LangGraph** (not CrewAI) — with a CrewAI-simple declarative layer

Use LangGraph for both the single-agent runtime and the multi-agent coordinator. CrewAI is not used, but the ergonomics gap that makes CrewAI attractive is closed directly rather than accepted as a trade-off.

**Why LangGraph and not CrewAI**
- One runtime, one state model, one mental model — CrewAI would introduce a second abstraction with its own memory, tools and telemetry to reconcile.
- Native LangSmith tracing: one run tree spanning coordinator → sub-agents → tools, for free. With CrewAI it needs glue.
- Durable execution: checkpointers, thread-scoped state, resume-after-failure, time-travel debugging.
- `interrupt()` gives real human-in-the-loop approval gates — required by the spec workflow's `/plan` approval step (see §1.6).
- Deterministic, inspectable control flow vs. CrewAI's role-play delegation, which is harder to test and budget.

**Closing the simplicity gap — two API layers, not one**

CrewAI's appeal is a declarative surface: declare agents and tasks, not control flow. `agentcore.graphs` provides the same surface on top of LangGraph:

```python
supervisor = build_supervisor(
    specialists=["AGT-011-researcher", "AGT-012-writer"],
    routing="auto",
)
supervisor.run(input)
```

No `StateGraph`, no manual edges, no hand-written state schema for the common case — `build_supervisor()` reads each `AGT-` spec (model tier, tools, budget) and wires the graph. Tracing, checkpointing, `interrupt()`, and budget enforcement come along automatically because it's still LangGraph underneath. When a project needs real control-flow logic — conditional routing, a mid-flow approval gate, parallel fan-out — it drops one level to the underlying LangGraph objects `build_supervisor` would have built, rather than hitting a wall and switching frameworks.

**P0 exit criterion:** a new supervisor with two specialists can be stood up in under 15 lines, with no direct `StateGraph` calls.

**Escape hatch (unused by default):** an adapter interface (`agentcore.orchestration.Runnable`) lets a CrewAI crew be wrapped as a single LangGraph node, if a specific project ever needs it.

**Default topology:** supervisor + specialist subgraphs, each with its own state schema, tool allowlist and model tier. Handoffs via `Command(goto=..., update=...)`.

### 1.2 Package & environment management: **UV**

- `uv` workspace monorepo *within* the framework repo (`agentcore` + its own tests/docs — see §1.5 for why generated projects are NOT part of this workspace).
- `uv.lock` committed; CI uses `uv sync --frozen`.
- `.python-version` pins the interpreter (3.12 baseline, 3.13 in the matrix).
- Dependency groups: `dev`, `test`, `eval`, `docs`, `lint`; extras per integration (`[postgres]`, `[mcp]`, `[langsmith]`, `[self-hosted-llm]`).
- `uv run` is the only sanctioned entrypoint.
- Docker: multi-stage build on the `ghcr.io/astral-sh/uv` image, `--frozen --no-dev`, bytecode compile, non-root runtime.

### 1.3 Spec-driven development: the cornerstone

Specs are versioned artifacts under `specs/`. Each has an ID that propagates into code, tests, traces and evals — and each declares **what it governs**.

**Spec taxonomy**

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

**Spec file shape** — YAML frontmatter (machine-readable) + Markdown body (human-readable):

```yaml
---
id: AGT-014
title: Contract Risk Extractor
status: approved          # draft | in_review | approved | deprecated
version: 2.1.0
owner: "@name"
model_tier: versatile
tools: [mcp:filesystem.read, mcp:postgres.query]
data_sources: [DS-003]
budget: { max_tokens_per_run: 40000, max_usd_per_run: 0.35, max_tool_calls: 12 }
io:
  input_schema: schemas/contract_input.json
  output_schema: schemas/risk_report.json
governs:
  paths:
    - "src/agents/risk_extractor/**"
    - "prompts/contracts/risk_*.md"
    - "tests/agents/test_contract_risk.py"
acceptance:
  - id: AC-1
    given: "a contract PDF with an auto-renewal clause"
    then: "output.risks contains a RENEWAL risk with clause citation"
    verified_by: tests/agents/test_contract_risk.py::test_renewal
  - id: AC-2
    then: "p95 latency < 20s and cost < $0.35 per run"
    verified_by: eval:EVL-004
---
```

`DS-` specs follow the same shape with a data-focused body: `classification`, `governs.resources` (URIs), `access.allowed_tables`, `access.denied_columns`, `access.max_rows`, `semantics` (link to a data dictionary), `freshness`.

`OPS-` specs record the three generation-time choices from §1.5–1.7 per project, so they're governed decisions with a paper trail, not just copier flags lost to history.

**Lifecycle:** `/specify` → `/clarify` → `/plan` → `/tasks` → `/implement` → `/verify` → `/accept`.

### 1.4 Traceability: **LangSmith**

- Tracing on by default. Every run tagged: `spec_id`, `spec_version`, `agent`, `graph`, `git_sha`, `env`, `session_id`, `tenant`, `model_tier`, `ds_spec_id` for any data source touched.
- Budget middleware raises `BudgetExceeded` and annotates the trace on breach.
- Datasets per `EVL-` spec; evaluators = LLM-as-judge (rubric from acceptance criteria) + deterministic assertions + cost/latency thresholds.
- PR comment bot posts eval delta vs. `main` baseline; regression beyond threshold blocks merge.
- Redaction is governed, not discretionary — see §1.6.
- Deployment target for LangSmith itself: see §1.6.

### 1.5 Repo topology: **framework repo + separate generated project repos**

**Locked.** `agent-forge` is framework-only — `agentcore`, spec templates, workflow definitions, the copier template. No real agent runs out of this repo.

Each real project is generated into its **own separate repo**:
```
copier copy gh:yourorg/agent-forge my-project
```
`agentcore` is pulled in as a pinned dependency via `uv`, not copied. Framework improvements arrive later via `copier update` inside the project repo — pulled deliberately, not automatically, so a project doesn't break mid-sprint on an unrelated framework change.

**Consequence — `agentcore` needs its own semantic versioning discipline**, so a breaking change is visible as a major version bump before `copier update` pulls it in, not discovered as a runtime failure. `docs/` carries a short "upgrading agentcore" guide covering the `copier update` cadence and who owns pulling it per project.

### 1.6 Generation-time configuration (copier prompts)

Three of the previously-open decisions resolve to the same pattern: **ask once, when the project is generated, not once in this document.** All three are recorded in the generated project's `OPS-001` spec.

| Prompt | Options | What it scaffolds |
|---|---|---|
| `deploy_target` | `self_hosted` \| `langgraph_platform` (Cloud or Hybrid sub-flag) | Both paths ship in `deploy/` regardless of choice (see §9); the selected one is wired into `deploy.yml` by default |
| `providers` (multi-select) | `openai`, `anthropic`, `azure_openai`, `bedrock`, `vertex`, `self_hosted` | `configs/models.yaml` pre-filled per tier for selected providers; `.env.example` lists exactly the credentials needed; self-hosted adapter code is only scaffolded if `self_hosted` is selected — all API-based adapters ship regardless, since `init_chat_model` covers them uniformly at no extra cost |
| `langsmith_target` | `cloud` \| `self_hosted` | `cloud`: API key in `.env.example`, nothing to deploy. `self_hosted`: `deploy/langsmith/self-hosted/` compose/K8s manifests included |

**Redaction is not a separate policy decision** — it keys off the `DS-` spec's `classification` field automatically, in `agentcore.observability`. If `langsmith_target=self_hosted`, traces never leave the VPC and full payloads are acceptable. If `cloud`, anything above a configurable sensitivity threshold is redacted before the trace leaves — enforced code, not developer discipline. A governance test asserts a `confidential`-classified data source never produces an unredacted trace payload when the cloud target is selected.

`template-test.yml` exercises both `deploy_target` values and both `langsmith_target` values (see §9) — capped to the meaningful combinations rather than the full cross-product.

### 1.7 CI host: **GitHub only**

**Locked, no portability layer.** No GitLab/Azure DevOps equivalents are built or maintained. `.github/` is the only home for workflows, prompts, CODEOWNERS, templates. GitHub-specific integrations (GHCR, GitHub App auth for the `github` MCP server, GitHub environments for approval gating, Renovate, branch protection) are used without a compatibility shim.

---

## 2. Enforcement ladder

Six layers, ordered by how much they actually bind. Design the weak layers for ergonomics; rely on the strong ones.

| # | Layer | Binds? | Feedback latency | Portable across tools? |
|---|---|---|---|---|
| 1 | **Spec as runtime dependency** — the agent loads its spec to run at all | Structurally | Instant (won't boot) | Yes |
| 2 | **CI gates** — spec-guard, orphan check, eval regression | Yes | Minutes (PR) | Yes (GitHub only, per §1.7) |
| 3 | **Local hooks** — PreToolUse block + inject; git pre-commit | Yes, deterministically | Seconds | Partly (Claude Code + git) |
| 4 | **MCP spec-server ergonomics** — the spec route is the cheapest route | No — makes compliance easiest | Seconds | Yes (MCP clients) |
| 5 | **Skill** — auto-triggers on task shape | No — raises trigger rate | Seconds | Claude-family + `.agents/skills` readers |
| 6 | **AGENTS.md** — thin instruction baseline | No | — | Yes (20+ tools) |

**Operating principle:** any AGENTS.md rule that is repeatedly ignored gets promoted into layer 3 or 2.

---

## 3. Making specs load-bearing (layer 1)

- The agent factory reads `AGT-*.yaml` **at runtime**, not as one-time codegen. Delete the spec → the agent doesn't start. Edit the spec → the running system changes.
- The MCP data-source proxy (`GovernedClient`) reads `DS-*.yaml` **on every call**.
- Graph construction reads `GRP-*.yaml` for topology and termination.
- Eval jobs read `EVL-*.yaml` for datasets and thresholds.
- The runtime itself reads `OPS-001` for deploy target, provider(s), and LangSmith target — so a project's generation-time choices are enforced the same way as everything else, not just documented.

Consequence: spec/code drift becomes something the system can't express, not something CI has to catch after the fact.

---

## 4. Spec binding: how a model knows which spec applies

### 4.1 Ownership declaration and index

Every spec declares a `governs:` block: **paths** (globs) and/or **resources** (URIs — MCP servers, database tables, datasets, API endpoints). `forge spec index` compiles these into `.spec-index.json`, committed so hooks resolve offline in milliseconds.

Invariants, checked by `spec_lint`:
- **No orphans** — every file under a governed root resolves to at least one spec.
- **No ambiguity** — two specs may not claim the same path unless one `extends` the other.
- **No dangling** — every glob matches a real path; every resource URI matches a configured MCP server.
- **Longest-match wins** for nested ownership.

### 4.2 The resolver

One function: `spec_for(target)` — file path, module, table, MCP server, dataset, or endpoint. Exposed four ways, same index:
- CLI: `forge spec for src/agents/risk_extractor/nodes.py`
- MCP tool: `spec_for_target(uri)`
- Python: `agentcore.specs.resolve(target)`
- Hook script: `scripts/hooks/resolve_spec.py`

### 4.3 Binding at each moment

**Authoring — file edits**
1. **PreToolUse hook** (`Edit|Write`) resolves the target path and either injects the governing spec's ACs and constraints via `additionalContext`, or exits 2 — blocking the write and feeding stderr back to the model with the exact next command (`spec_create --governs <path>`). Configured in `.claude/settings.json`, committed, so it ships with the clone.
2. **PostToolUse hook** re-runs `spec_lint --changed` and returns violations as feedback.
3. **Nested `AGENTS.md`** in every governed directory — cross-tool fallback for editors without hooks.
4. **`spec-workflow` skill** — auto-triggers on agent/graph/tool/eval work, carries templates and scripts.
5. **MCP tool descriptions** on the spec-server state the policy directly — loaded whenever the server is connected.

*Known gap:* `@`-mentioned files bypass PreToolUse (no tool call fires). CI (layer 2) catches this at PR time.

**Authoring — data sources.** Same resolver, resource-keyed: `spec_for("mcp:postgres://warehouse/contracts")` returns `DS-003` before a query is written, surfacing the data dictionary, join keys, freshness caveat and denied columns.

**Runtime — data calls.** Every MCP data call routes through `GovernedClient`, which resolves the `DS-` spec and enforces it in-process: rejects non-allowlisted tables/operations, strips denied columns, injects `LIMIT`, appends the freshness caveat to the tool result, tags the trace with `ds_spec_id` + `classification`. An unspecced data source is unreachable.

**Review — PR time.** Changed files → governing specs → must be `approved`, bound tests pass, relevant `EVL-` evals run. Orphan check fails the PR if a governed root gained an unowned file. PR bot comments the affected specs/ACs. An approved spec whose ACs changed without a version bump fails the build.

### 4.4 Traceability chain

```
spec (governs: paths + resources)
  → resolver index
    → code annotation @spec("AGT-014", "AC-1")
      → test bound to AC
        → LangSmith run metadata (spec_id, spec_version, ds_spec_id, git_sha)
          → eval dataset
```

`forge spec trace AGT-014` walks it in both directions.

---

## 5. Framework repository layout (`agent-forge` itself)

```
agent-forge/
├── AGENTS.md                       # thin (~40 lines)
├── CLAUDE.md -> AGENTS.md
├── .github/
│   ├── copilot-instructions.md -> ../AGENTS.md
│   ├── workflows/                  # see §9 — GitHub-only, per §1.7
│   ├── prompts/*.prompt.md         # /specify /plan /tasks /implement
│   ├── ISSUE_TEMPLATE/spec.yml
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── CODEOWNERS
├── .claude/
│   ├── settings.json               # committed hooks config (§4.3)
│   ├── skills/spec-workflow/
│   └── commands/*.md
├── .mcp.json
├── specs/
│   ├── constitution.md             # CON-001 — includes HITL rule, §1.6 caveat
│   ├── agents/ graphs/ tools/ data_sources/ evals/ ops/ adr/
│   ├── templates/                  # one per spec kind, includes OPS- template capturing §1.6 choices
│   └── schema/spec.schema.json
├── .spec-index.json
├── src/
│   └── agentcore/
│       ├── specs/                  # loader, resolver, index builder, lint
│       ├── config/  llm/           # llm/ ships all API adapters + optional self-hosted adapter
│       ├── prompts/
│       ├── agents/                 # factory reads AGT specs at runtime
│       ├── graphs/                 # build_supervisor/build_pipeline/build_map_reduce (§1.1) + raw LangGraph escape hatch
│       ├── tools/
│       ├── mcp/                    # GovernedClient, DS enforcement, manager
│       ├── memory/  budget/  observability/  evals/
│       └── cli/                    # `forge`
├── tests/{unit,contract,integration,evals}/  + fixtures/cassettes/
├── configs/
│   ├── models.yaml.template        # filled per §1.6 provider selection at generation time
│   └── environments/{local,dev,staging,prod}.yaml.template
├── scripts/
│   ├── spec_lint.py  spec_index.py  cost_report.py  dataset_sync.py
│   └── hooks/{resolve_spec.py,pre_edit.py,post_edit.py}
├── servers/spec_server/            # our MCP server (§7)
├── docs/                           # includes "upgrading agentcore" (§1.5), "resuming a paused run" (§1.8)
├── deploy/
│   ├── self-hosted/                # Dockerfile, compose/K8s, Postgres checkpointer
│   └── langgraph-platform/         # langgraph.json, deploy CI step
├── template/                       # copier template — prompts from §1.6
├── pyproject.toml  uv.lock  .python-version
├── Makefile  .pre-commit-config.yaml
```

*(A generated project repo has the same `src/`, `specs/`, `tests/`, `.claude/`, `.github/` shape, minus the `template/` directory, plus its own `OPS-001` recording the §1.6 choices it was generated with.)*

---

## 6. Core framework components (`agentcore`)

1. **Specs** — pydantic models per kind, JSON Schema export, loader with version pinning, resolver, index builder, linter.
2. **Config** — `pydantic-settings`, layered: defaults → environment YAML → env vars → CLI. Secrets never in files.
3. **ModelRouter** — tiers in `models.yaml`: `light`, `versatile`, `reasoning`, `auto`. Provider-agnostic via `init_chat_model` for all API-based providers (§1.6); a distinct self-hosted adapter for local/private models, scaffolded only when selected. Per-tier fallback chains; prompt-caching flags.
4. **Prompt system** — RAIL sections as files, cache-first composition, Jinja2-rendered, content-hashed for trace pinning.
5. **Agent factory** — spec in, compiled LangGraph agent out.
6. **Graph builders** — declarative layer (`build_supervisor`, `build_pipeline`, `build_map_reduce`, `explore_subagent`) per §1.1, plus the underlying LangGraph objects for the 20% case needing custom control flow.
7. **MCP layer** — server manager, lazy loading, per-agent allowlists, `GovernedClient` enforcing `DS-` specs.
8. **Memory** — checkpointer: in-memory (tests) → SQLite (local) → Postgres (prod, either self-hosted or Platform-managed per §1.6); long-term store; state trimming policy.
9. **Budget middleware** — pre-flight estimate, running counter, soft warn / hard stop, LangSmith annotation on breach.
10. **Guardrails** — I/O validation, PII redaction (keyed off `DS-` classification, §1.6), loop/max-iteration detection.
11. **`forge` CLI** — `new-agent`, `spec {new,lint,index,for,trace}`, `run`, `resume <thread_id>` (§1.8), `status`, `eval`, `cost report`, `mcp doctor`.

---

## 7. MCP strategy

| Server | Use | Default scope |
|---|---|---|
| **`spec-server` (we build it)** | resolver + spec CRUD + scaffolding | read/write to `specs/` |
| `filesystem` | repo/file reads | read-only, path-restricted |
| `git` | history, blame, diff context | read-only |
| `github` | issues, PRs, CI status | least-privilege App (§1.7) |
| `fetch` | web/document retrieval | domain allowlist |
| `postgres` / `sqlite` | systems of record, behind `GovernedClient` | read-only role + `DS-` spec |
| `playwright` | browser tasks, E2E | dev only |
| `context7` (or equivalent docs server) | current library docs | read-only |
| `langsmith` (optional) | agents query their own traces/evals | read-only |

Spec-server capped at ~8 tools: `spec_for_target`, `spec_get`, `spec_search`, `spec_create`, `next_task`, `bind_test`, `scaffold_agent`, `spec_lint`. Tool descriptions carry policy (`scaffold_agent` refuses without an approved spec). Also exposes `/specify`/`/plan`/`/tasks` as MCP prompts and specs as MCP resources.

---

## 8. Testing strategy

| Layer | What | Runs |
|---|---|---|
| Unit | Routers, budget math, prompt assembly, resolver | every PR, no network |
| Spec contract | Schema validation, path resolution, AC binding | every PR |
| Recorded integration | Full graph runs against cassette-recorded responses | every PR |
| Governance | `GovernedClient` blocks denied columns / unspecced resources / over-limit queries; cloud-redaction test (§1.6) | every PR |
| Live smoke | Small set against real providers | `main`, nightly |
| Evals | LangSmith datasets per `EVL-` spec | selective on PR, nightly, pre-release |

A pytest plugin collects ACs from specs and fails a placeholder for every unbound one. Coverage floor 80% on `agentcore`. Eval thresholds are N-run medians with ranges.

---

## 9. CI/CD (GitHub Actions only, per §1.7)

**Pre-commit:** ruff format+lint, mypy (strict on `agentcore`), `spec_lint --changed`, index freshness, gitleaks, uv lock check, conventional commits.

**Workflows**

1. `ci.yml` — uv sync `--frozen` → ruff → mypy → pytest (unit, contract, governance, recorded) on {3.12, 3.13} → coverage gate → docs build.
2. `spec-guard.yml` — schema validation, index freshness, orphan check, ambiguity check, changed-files→specs resolution, status must be `approved`, AC-change-without-version-bump fails, PR bot comment.
3. `security.yml` — `uv pip audit`, gitleaks, CodeQL, Trivy on the image, CycloneDX SBOM on releases.
4. `evals.yml` — selective (touched specs), nightly (full), pre-release. Baseline comparison, delta comment, fails on regression or cost breach.
5. `build.yml` — multi-arch image → GHCR, cosign-signed, provenance attestation.
6. `deploy.yml` — branches on the project's `OPS-001` deploy target (§1.6) via a repo variable; dev auto → staging auto → prod manual approval; post-deploy smoke; auto-rollback. Same file works for either target — no hand-edited YAML per project.
7. `release.yml` — semantic-release: version, changelog, tag, publish package + image + docs. `agentcore` itself follows strict semver per §1.5.
8. `template-test.yml` — generates the template across the meaningful `(deploy_target, langsmith_target)` combinations (not the full cross-product — e.g., self-hosted+self-hosted and platform+cloud as the two primary pairs, plus one cross combination), runs each through full CI. Guarantees neither deploy path nor either LangSmith path rots.
9. `cost-report.yml` — weekly LangSmith cost/token report per project and per agent.

**Hygiene:** branch protection, required checks, CODEOWNERS on `specs/`, Renovate (grouped, auto-merge patch), OIDC to cloud (no long-lived keys), per-environment secrets.

---

## 10. Reusability: project generation

```
copier copy gh:yourorg/agent-forge my-project
```

Prompts (§1.6): `deploy_target`, `providers` (multi-select), `langsmith_target`, plus topology (single / supervisor / pipeline) and persistence (sqlite/postgres).

Generated repo ships with: UV workspace, pinned `agentcore`, constitution (including the HITL rule from §1.8), one `AGT-` and one `DS-` spec, a working agent, committed hooks and skill, `OPS-001` recording every generation-time choice, all nine workflows pre-wired to the selected targets, docs. `copier update` pulls framework improvements in later (§1.5).

---

## 11. Milestones

| Phase | Deliverable | Exit criteria |
|---|---|---|
| **P0 — Foundations** | UV workspace, skeleton, pre-commit, `ci.yml`, thin `AGENTS.md`, `CON-001` (incl. HITL rule), spec templates | Empty repo green in CI; a two-specialist supervisor stands up in <15 lines (§1.1) |
| **P1 — Spec engine** | Pydantic spec models, JSON Schema, loader, `spec_lint`, `@spec` annotations, `spec-guard.yml` | A spec with no verifying test fails CI |
| **P2 — Binding layer** | `governs:` blocks, index builder, resolver, `forge spec for`, orphan/ambiguity checks, hooks, nested AGENTS.md, `spec-workflow` skill | Editing an unowned file is blocked locally; editing an owned file auto-loads its spec |
| **P3 — Agent runtime** | Config, ModelRouter (all API adapters + optional self-hosted), RAIL prompts, runtime spec-loading factory, budget middleware, LangSmith wiring (both targets) | A freshly generated project runs its first traced agent with only `.env` filled in, on whichever provider(s)/LangSmith target were selected |
| **P4 — Data & MCP governance** | `DS-` specs, `GovernedClient`, MCP manager, `spec-server`, `mcp doctor`, cloud-redaction enforcement | A query hitting a denied column is blocked at runtime and traced; confidential data never appears unredacted when `langsmith_target=cloud` |
| **P5 — Multi-agent** | `build_supervisor`/`build_pipeline`/`build_map_reduce`, explore sub-agent, `GRP-` specs | Reference project: supervisor + 2 specialists + 2 MCP servers, one trace tree end-to-end |
| **P6 — Evals & gates** | Dataset sync, AC-derived evaluators, selective `evals.yml`, baselines, cost report | A deliberate quality regression is blocked by CI |
| **P7 — Delivery** | Both deploy paths (`deploy/self-hosted/`, `deploy/langgraph-platform/`), `deploy.yml` branching on `OPS-001`, release automation, security workflows, SBOM | One-click dev deploy on **both** deploy targets; prod approval gate working on whichever is selected |
| **P8 — Templatization** | Copier template with all §1.6 prompts, `template-test.yml` across target combinations, docs (`copier update` cadence, `forge resume`) | A freshly generated project — on any prompted combination — passes its own CI unmodified |

---

## 12. Locked configuration reference

Every decision that was open is now fixed. This replaces the old "open decisions" list.

| # | Decision | Resolution |
|---|---|---|
| 1 | Deployment target | **Both** self-hosted and LangGraph Platform (Cloud/Hybrid), chosen per-project via copier; both paths built and tested in `template-test.yml` |
| 2 | Model providers | Chosen per-project via copier (multi-select); all API-based adapters ship by default, self-hosted adapter scaffolded only when selected |
| 3 | LangSmith target | Chosen per-project via copier (cloud/self-hosted); redaction enforcement keyed off `DS-` classification automatically, independent of target |
| 4 | CI host | **GitHub only** — no portability layer |
| 5 | Repo topology | **Model A** — `agent-forge` is framework-only; every real project is a separate repo generated via `copier copy`, updated via `copier update` |
| 6 | Human-in-the-loop | **CLI only.** `forge resume <thread_id>` for paused background runs. Constitution rule: unattended/scheduled graphs must not use runtime `/plan`-style `interrupt()` gates — pre-approve at the spec level instead |
| 7 | Ownership granularity | **Fine-grained** `governs:` per agent/prompt file; **coarse** per-module for shared `agentcore` utilities |

---

## 13. Definition of done for the repo itself

- A new project is generated and running a traced agent in under 15 minutes, on whichever deploy/provider/LangSmith combination was selected.
- A coding agent editing any governed file receives that file's spec automatically, without being asked.
- A coding agent touching any data source receives that source's schema, semantics and constraints — and cannot exceed them at runtime.
- No agent ships without a spec, tests bound to acceptance criteria, and a budget.
- Every production run is reconstructible: trace → git SHA → prompt version → spec ID + version → data sources touched.
- `uv sync --frozen && uv run pytest` is the entire local setup story.
- Cost per run is visible per agent, per project, per week, without opening a provider console.
- No open decisions remain — every generation-time choice is a copier prompt with both/all paths built, tested, and governed by `OPS-001`.
