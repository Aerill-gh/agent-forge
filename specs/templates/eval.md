---
id: EVL-NNN
title: <Eval name>
status: draft
version: 0.1.0
owner: "@name"
subject: AGT-NNN            # or GRP-NNN
dataset: datasets/<name>.jsonl
evaluators:
  - kind: llm_judge
    rubric: "<derived from subject's acceptance criteria>"
  - kind: deterministic
    assertion: "<e.g. output schema validates>"
  - kind: cost_latency
    max_usd_per_run: 0.35
    p95_latency_seconds: 20
thresholds:
  min_pass_rate: 0.9
  regression_policy: "block merge if pass_rate drops > 5pp vs main baseline, N=5 run median"
governs:
  paths:
    - "tests/evals/test_<name>.py"
---

# EVL-NNN — <Eval name>

## Dataset

<Where it comes from, how it's kept in sync — `dataset_sync.py`.>

## Evaluators

<Rationale for each evaluator and its threshold.>
