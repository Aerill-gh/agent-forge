---
id: TOOL-NNN
title: <Tool / MCP server name>
status: draft
version: 0.1.0
owner: "@name"
kind: mcp_server            # mcp_server | local_tool
scopes: []                   # e.g. [filesystem:read, postgres:query]
rate_limits:
  max_calls_per_run: 12
  max_calls_per_minute: 30
data_classification: internal   # public | internal | confidential
governs:
  resources:
    - "mcp:<server>"
acceptance:
  - id: AC-1
    then: "<contract guarantee, e.g. denied scopes are rejected>"
    verified_by: tests/contract/test_<name>.py::test_<case>
---

# TOOL-NNN — <Tool / MCP server name>

## Contract

<What this tool/server does, its scopes, and what it must refuse.>

## Least privilege

<Why this scope list is the minimum needed — reviewers check this against
tool-count budget in CI.>
