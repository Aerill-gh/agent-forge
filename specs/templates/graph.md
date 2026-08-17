---
id: GRP-NNN
title: <Graph name>
status: draft
version: 0.1.0
owner: "@name"
topology: supervisor      # supervisor | pipeline | map_reduce | custom
specialists: []            # AGT- spec ids, in handoff order if relevant
termination:
  condition: "<when the graph stops>"
  max_turns: 20
escalation:
  condition: "<when to hand off to a human / interrupt()>"
governs:
  paths:
    - "src/graphs/<name>/**"
    - "tests/graphs/test_<name>.py"
acceptance:
  - id: AC-1
    given: "<precondition>"
    then: "<expected handoff/termination behavior>"
    verified_by: tests/graphs/test_<name>.py::test_<case>
---

# GRP-NNN — <Graph name>

## Topology

<Diagram or description of supervisor/specialist wiring, handoffs via
`Command(goto=..., update=...)`.>

## Termination & escalation

<Explicit rules — must not rely on runtime `interrupt()` if this graph runs
unattended (CON-001 §4).>
