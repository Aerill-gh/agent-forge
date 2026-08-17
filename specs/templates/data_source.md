---
id: DS-NNN
title: <Data source name>
status: draft
version: 0.1.0
owner: "@name"
classification: internal    # public | internal | confidential
governs:
  resources:
    - "mcp:<server>://<host>/<database>"
access:
  allowed_tables: []
  denied_columns: []
  max_rows: 1000
semantics: docs/data-dictionary/<name>.md
freshness: "<e.g. updated nightly at 02:00 UTC>"
acceptance:
  - id: AC-1
    then: "queries against denied_columns are rejected at runtime"
    verified_by: tests/governance/test_<name>.py::test_denied_column_blocked
---

# DS-NNN — <Data source name>

## Schema & semantics

<Link to data dictionary; note join keys, gotchas, units.>

## Access policy

<Why these tables/columns are allowed or denied; who owns exceptions.>

## Freshness

<Caveat that GovernedClient appends to every tool result.>
