---
id: ADR-004
title: Agent runtime — config, ModelRouter, RAIL prompts, factory, budget
status: approved
version: 1.0.0
owner: "@vachik"
date: 2026-08-17
extends: ADR-001
governs:
  paths:
    - "src/agentcore/config/**"
    - "src/agentcore/llm/**"
    - "src/agentcore/prompts/**"
    - "src/agentcore/agents/**"
    - "src/agentcore/budget/**"
    - "src/agentcore/observability/**"
    - "prompts/**"
    - "configs/**"
    - "tests/unit/test_config*.py"
    - "tests/unit/test_llm*.py"
    - "tests/unit/test_prompts*.py"
    - "tests/unit/test_agents*.py"
    - "tests/unit/test_budget*.py"
    - "tests/unit/test_observability*.py"
acceptance:
  - id: AC-1
    given: "a layered config (defaults, an environment YAML, env vars) and no secrets in any file"
    then: "load_config() merges them with env vars winning, and validates via pydantic-settings"
    verified_by: tests/unit/test_config.py::test_load_config_layers_and_env_wins
  - id: AC-2
    given: "an AGT- spec's model_tier and models.yaml's tier -> provider-model mapping"
    then: "ModelRouter.for_tier() returns a chat model built via a provided factory (init_chat_model in production, injectable for tests)"
    verified_by: tests/unit/test_llm.py::test_router_resolves_tier_via_factory
  - id: AC-3
    given: "a tier with a fallback chain and a primary that raises"
    then: "ModelRouter falls back to the next model in the chain"
    verified_by: tests/unit/test_llm.py::test_router_falls_back_on_primary_failure
  - id: AC-4
    given: "a RAIL prompt file with Role/Action/Information/Limits sections"
    then: "render_prompt() Jinja2-renders it and lint_rail() passes; a prompt missing Limits fails lint_rail()"
    verified_by: tests/unit/test_prompts.py::test_render_and_lint_rail
  - id: AC-5
    given: "an AGT- spec, a fake chat model factory, and no tools"
    then: "build_agent(spec) returns a compiled LangGraph agent that runs a full turn end-to-end"
    verified_by: tests/unit/test_agents.py::test_build_agent_runs_a_turn_with_fake_model
  - id: AC-6
    given: "a budget (max_tokens_per_run, max_usd_per_run, max_tool_calls) and a running counter"
    then: "BudgetTracker soft-warns past 80% and raises BudgetExceeded past 100% of any dimension"
    verified_by: tests/unit/test_budget.py::test_budget_tracker_warns_then_raises
  - id: AC-7
    given: "an OPS- spec's langsmith_target (cloud | self_hosted)"
    then: "configure_langsmith(ops) sets LANGCHAIN_TRACING_V2/LANGCHAIN_PROJECT/LANGCHAIN_ENDPOINT correctly for each target"
    verified_by: tests/unit/test_observability.py::test_configure_langsmith_per_target
---

# ADR-004 — Agent runtime

## Context

P1/P2 made specs loadable, indexed, and enforced. Nothing yet turns an
`AGT-` spec into a running agent — the plan's §6 core-components list
(config, `ModelRouter`, prompt system, agent factory, budget middleware,
LangSmith wiring) is still all stub `__init__.py` files. Per `CLAUDE.md`,
this framework repo runs no real agent — the P3 exit criterion in the
plan's §11 ("a freshly generated project runs its first traced agent")
describes a *generated* project's behavior, verified end-to-end only once
the copier template exists (P8, `template-test.yml`). What this ADR
delivers instead is the reusable machinery that criterion depends on, each
piece verified in this repo's own tests against a fake/injected model —
never a live provider call, since no API credentials exist here.

## Decision

- **`config/`** — `pydantic-settings`-based `AppConfig`, layered
  defaults -> `configs/environments/<env>.yaml` -> environment variables
  (env vars win). No secrets in YAML — `AppConfig` fields for API keys are
  `SecretStr` sourced only from env vars. `configs/models.yaml.template`
  and `configs/environments/*.yaml.template` are the checked-in templates
  a generated project fills in.
- **`llm/`** — `ModelRouter`, tiers `light | versatile | reasoning | auto`
  read from `models.yaml`, each tier a fallback chain of provider-model
  strings. Model construction is provider-agnostic via an injectable
  `model_factory: Callable[[str], BaseChatModel]` defaulting to
  `langchain.chat_models.init_chat_model` — this is what makes "all API
  adapters" (plan §6.3) fall out of one function instead of one adapter
  class per provider. A self-hosted adapter is a distinct factory
  (OpenAI-compatible `base_url`) scaffolded but not exercised here (no
  local model server in this environment).
- **`prompts/`** (module) — RAIL prompt files live under the top-level
  `prompts/` directory (governed content, same shape as `specs/`).
  `render_prompt()` Jinja2-renders a template with content-hash pinning
  for trace metadata; `lint_rail()` fails a prompt file missing a
  `## Limits` section, per the plan's §0 RAIL principle.
- **`agents/`** — `build_agent(spec: AgentSpec, model_factory=...) ->
  CompiledStateGraph` reads an `AGT-` spec's `model_tier`, resolves a
  model via `ModelRouter`, renders its RAIL prompt as the system prompt,
  and compiles a `langchain.agents.create_agent` graph (tools default to
  `[]` — real tool wiring is `TOOL-`/MCP, P4). This is the "spec in,
  compiled LangGraph agent out" factory from plan §6.5.
- **`budget/`** — `BudgetTracker(budget: Budget)` (the `Budget` model
  already on `AgentSpec`, ADR-001) tracks tokens/USD/tool-calls per run,
  soft-warns at 80% of any dimension, raises `BudgetExceeded` at 100% —
  pure Python, no external dependency.
- **`observability/`** — `configure_langsmith(ops: OpsSpec)` sets
  `LANGCHAIN_TRACING_V2`/`LANGCHAIN_PROJECT`/`LANGCHAIN_ENDPOINT` from an
  `OPS-` spec's `langsmith_target` field — `cloud` (default endpoint) or
  `self_hosted` (requires `langsmith_endpoint`). `OpsSpec` gains
  `deploy_target`, `providers`, `langsmith_target`, `langsmith_endpoint`
  fields (previously an empty stub, though `specs/templates/ops.md`
  already anticipated this shape in P0) to carry the generation-time
  choices from plan §1.6/§12 — every generated project traces somewhere,
  there is no "off" option per the locked config reference.
- **CLI** — none added here; `forge run`/`forge status` are explicitly
  P3+ follow-ups once a generated project has a real `.env`, not
  something this framework repo can demonstrate against a live provider.

## Alternatives considered

- **Hardcode a per-provider `ChatAnthropic`/`ChatOpenAI` adapter class
  per provider.** Rejected: `init_chat_model` already gives
  provider-agnostic construction from a `"provider:model"` string; a
  per-provider class ladder is exactly the maintenance burden the plan's
  §1.6 decision (all API adapters ship by default) is trying to avoid.
- **Skip the fake-model test coverage and mark agent-runtime code
  "integration only, verify in a generated project."** Rejected: per
  `CON-001`, no acceptance criterion ships without a verifying test, and
  `spec_lint` would fail the build on any `verified_by` that doesn't
  resolve. `FakeListChatModel` (from `langchain-core`) makes real
  end-to-end graph-compile-and-run coverage possible without a network
  call or credentials.
- **Use `tiktoken` for exact token estimates in `BudgetTracker`.**
  Rejected for this pass: `tiktoken` is provider/model-specific and pulls
  a real tokenizer dependency for a pre-flight *estimate* that the plan
  itself only asks to be a soft-warn signal, not a billing-accurate
  count. A `len(text) // 4` heuristic is documented in the code as
  approximate; swapping in a real tokenizer later doesn't change the
  `BudgetTracker` interface.

## Consequences

- `agentcore.agents.build_agent` is the first piece of `agentcore` that
  imports `langchain`/`langgraph` — new mandatory dependencies
  (`langchain`, which pulls `langgraph` and `langchain-core`),
  `pydantic-settings`, `jinja2`. `langsmith` is already an existing empty
  optional-dependency group in `pyproject.toml`; it gains a real
  dependency here since `configure_langsmith` needs the `langsmith`
  package's env-var contract, not just the concept.
- MCP tools, `DS-` enforcement, and multi-agent graph builders
  (`build_supervisor` etc.) are explicitly out of scope — P4 and P5 per
  the plan's milestone table.
- The self-hosted model adapter is scaffolded (a factory function exists,
  config fields exist) but has no test proving it works against a real
  local server — there is none in this environment. A generated project
  that selects the self-hosted provider is the actual verification point,
  same caveat as the P3 exit criterion itself.
