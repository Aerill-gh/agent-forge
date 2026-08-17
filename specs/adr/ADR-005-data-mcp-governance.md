---
id: ADR-005
title: Data & MCP governance — GovernedClient, MCP manager, spec-server
status: approved
version: 1.0.0
owner: "@vachik"
date: 2026-08-17
extends: ADR-004
governs:
  paths:
    - "src/agentcore/mcp/**"
    - "servers/spec_server/**"
    - "tests/unit/test_mcp*.py"
    - "tests/contract/test_spec_server.py"
acceptance:
  - id: AC-1
    given: "a DS- spec with access.allowed_tables and a query against a table not in that list"
    then: "GovernedClient.query() raises DeniedTable before the executor runs"
    verified_by: tests/unit/test_mcp.py::test_query_rejects_unallowlisted_table
  - id: AC-2
    given: "a DS- spec with access.denied_columns and a query explicitly requesting one"
    then: "GovernedClient.query() raises DeniedColumn before the executor runs"
    verified_by: tests/unit/test_mcp.py::test_query_rejects_explicit_denied_column
  - id: AC-3
    given: "a query with no explicit column list, whose executor returns rows containing a denied column"
    then: "GovernedClient.query() strips that column from every returned row and records it as redacted"
    verified_by: tests/unit/test_mcp.py::test_query_strips_denied_column_when_not_explicitly_requested
  - id: AC-4
    given: "a query with an explicit limit above access.max_rows"
    then: "GovernedClient.query() raises OverLimitQuery; an unspecified limit is auto-set to access.max_rows"
    verified_by: tests/unit/test_mcp.py::test_query_blocks_over_limit_and_defaults_limit
  - id: AC-5
    given: "a successful query"
    then: "the result carries ds_spec_id, classification, and the DS spec's freshness caveat"
    verified_by: tests/unit/test_mcp.py::test_query_result_tags_trace_metadata
  - id: AC-6
    given: "an OPS- spec with langsmith_target=cloud and a DS- spec classified confidential"
    then: "redact_for_trace() replaces row content with a summary; self_hosted or non-confidential leaves it untouched"
    verified_by: tests/unit/test_mcp.py::test_redact_for_trace_keyed_off_target_and_classification
  - id: AC-7
    given: "an AGT- spec's tools list and a registry of TOOL- specs"
    then: "MCPManager.resolve_allowlist() raises UnapprovedTool for a tool whose TOOL- spec isn't approved, and UnknownTool for one with no matching spec"
    verified_by: tests/unit/test_mcp.py::test_manager_rejects_unapproved_and_unknown_tools
  - id: AC-8
    given: "the spec-server MCP tool set"
    then: "it exposes exactly the 8 tools the plan's §7 budget names, callable in-process via call_tool"
    verified_by: tests/contract/test_spec_server.py::test_tool_budget_and_names
  - id: AC-9
    given: "scaffold_agent called against a draft (not approved) AGT- spec"
    then: "it refuses and returns an error, per the plan's §7 policy note"
    verified_by: tests/contract/test_spec_server.py::test_scaffold_agent_refuses_without_approved_spec
---

# ADR-005 — Data & MCP governance

## Context

P3 gave `agentcore` a runtime that can build and run an agent, but every
data source and MCP tool an agent might reach for is still unspecced and
unenforced — the plan's central guarantee (`CON-001` §1: "query a data
source -> its spec is enforced") has no code behind it yet. `DS-` and
`TOOL-` spec templates already existed from P0 with a precise shape
(`specs/templates/data_source.md`'s `access: {allowed_tables,
denied_columns, max_rows}` and its own acceptance criterion — "queries
against denied_columns are rejected at runtime" — which this ADR follows
literally rather than the looser "strips" wording in the plan's prose,
since the committed template is the more concrete, already-approved
contract).

## Decision

- **`specs/models.py`** — `DataSourceSpec` (`classification: public |
  internal | confidential`, `access: DataSourceAccess {allowed_tables,
  denied_columns, max_rows}`, `semantics`, `freshness`) and `ToolSpec`
  (`kind: mcp_server | local_tool`, `scopes`, `rate_limits
  {max_calls_per_run, max_calls_per_minute}`, `data_classification`) —
  both matching their P0 templates field-for-field.
- **`mcp/GovernedClient`** — `query(table, columns=None, operation="read",
  limit=None)`:
  - table not in `access.allowed_tables` -> `DeniedTable`, executor never
    runs.
  - any explicitly requested column in `access.denied_columns` ->
    `DeniedColumn`, executor never runs — this is the literal "rejected at
    runtime" the DS template's own AC asks for.
  - no explicit column list (caller wants everything) -> the executor
    runs, but any denied column present in the returned rows is stripped
    and recorded — the defensive case the plan's §4.3 prose describes
    ("strips denied columns") for data the caller didn't specifically ask
    for by name.
  - `limit` explicitly above `access.max_rows` -> `OverLimitQuery`; no
    `limit` given -> auto-set to `access.max_rows` (the "injects LIMIT"
    behavior from plan §4.3).
  - every result carries `ds_spec_id`, `classification`, and
    `access.freshness`-sourced caveat — the trace-tagging half of §4.3.
- **`mcp/redact_for_trace(payload, ds, ops)`** — the cloud-redaction rule
  from `specs/templates/ops.md`'s own doc: `self_hosted` target -> full
  payload (never leaves the VPC); `cloud` target and `classification ==
  "confidential"` -> row content replaced with a row-count-only summary;
  anything else passes through unredacted.
- **`mcp/MCPManager`** — `resolve_allowlist(agent_tools, tool_specs) ->
  list[ResolvedTool]`, resource-keyed against each `TOOL-` spec's
  `governs.resources` pattern (e.g. `mcp:postgres` matches an agent's
  `mcp:postgres.query` tool string by prefix). Raises `UnknownTool` (no
  matching `TOOL-` spec) or `UnapprovedTool` (spec exists but
  `status != approved`) — this is deliberately structural (allowlist
  resolution, lazy — no connection attempted) rather than a live MCP
  client manager, since no MCP server process runs in this environment.
- **`servers/spec_server/`** — a real `mcp.server.mcpserver.MCPServer`
  (package `mcp`, pinned `>=2.0`) exposing the plan's §7 8-tool budget:
  `spec_for_target`, `spec_get`, `spec_search`, `spec_create`,
  `next_task`, `bind_test`, `scaffold_agent`, `spec_lint` — each a thin
  wrapper over `agentcore.specs` functions already built in P1/P2.
  `scaffold_agent` refuses (per the plan's §7 policy-in-tool-description
  note) unless the target `AGT-` spec's `status == "approved"`. Tested
  in-process via `MCPServer.call_tool()` — no transport (stdio/SSE) is
  spun up, matching the "no real agent runs here" constraint.

## Alternatives considered

- **Follow the plan's §4.3 prose literally and only strip denied
  columns, never reject.** Rejected: the DS spec template itself, already
  approved in P0, states the acceptance criterion as "rejected at
  runtime," and a caller explicitly naming a denied column is a stronger
  signal of intent than one that merely receives it as part of `SELECT
  *` — rejecting the explicit case and stripping the incidental case
  satisfies both the template's literal AC and the plan's prose without
  contradiction.
- **Spin up spec-server over stdio/SSE and test through a real MCP
  client.** Rejected for this pass: `MCPServer.call_tool()` exercises the
  exact same tool-dispatch path a real client would hit, without needing
  a subprocess or transport in CI — a real-transport smoke test is a
  natural follow-up once a generated project actually runs this server,
  not something this framework repo's own test suite needs.
- **Build a live `MCPManager` that actually connects to configured MCP
  servers.** Rejected: no MCP servers run in this environment (framework
  repo, no real agent), so a "live" implementation would be untested
  code. The allowlist-resolution structure is the part with a real
  invariant to enforce and test; live session management is a generated
  project's concern.

## Consequences

- `GovernedClient` and `redact_for_trace` are pure Python — no real
  database driver dependency added; the executor is caller-injected
  (a fake in this repo's tests, a real `psycopg`/`sqlite3` call in a
  generated project).
- `mcp` (`>=2.0`) is now a dependency — the first MCP-protocol package in
  `agentcore`. Its `MCPServer` API differs from the older `FastMCP`
  examples common in MCP docs; `servers/spec_server/server.py` documents
  the exact import path used.
- `forge mcp doctor` (checking `TOOL-` spec rate-limit/scope well-formedness
  and the spec-server tool-count budget) is not built in this pass —
  noted as the natural next increment, not required by this ADR's
  acceptance criteria.
