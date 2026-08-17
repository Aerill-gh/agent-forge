---
id: AGT-NNN
title: <Agent name>
status: draft          # draft | in_review | approved | deprecated
version: 0.1.0
owner: "@name"
model_tier: versatile   # light | versatile | reasoning | auto
tools: []                # e.g. [mcp:filesystem.read, mcp:postgres.query]
data_sources: []         # DS- spec ids this agent may query
budget:
  max_tokens_per_run: 40000
  max_usd_per_run: 0.35
  max_tool_calls: 12
io:
  input_schema: schemas/<name>_input.json
  output_schema: schemas/<name>_output.json
governs:
  paths:
    - "src/agents/<name>/**"
    - "prompts/<domain>/<name>_*.md"
    - "tests/agents/test_<name>.py"
acceptance:
  - id: AC-1
    given: "<precondition>"
    then: "<expected behavior>"
    verified_by: tests/agents/test_<name>.py::test_<case>
  - id: AC-2
    then: "p95 latency < <N>s and cost < $<N> per run"
    verified_by: eval:EVL-NNN
---

# AGT-NNN — <Agent name>

## Role

<What this agent is responsible for, in one paragraph.>

## RAIL

- **Role:** <persona/expertise the prompt assumes>
- **Action:** <what the agent does each turn>
- **Information:** <what context/tools it's given>
- **Limits:** <what it must never do — required section, linted>

## Notes

<Anything a reviewer needs to approve this spec.>
