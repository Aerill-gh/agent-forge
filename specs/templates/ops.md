---
id: OPS-001
title: <Project name> — Operations
status: draft
version: 0.1.0
owner: "@name"
deploy_target: self_hosted        # self_hosted | langgraph_platform
langgraph_platform_mode: null      # cloud | hybrid — set only if deploy_target=langgraph_platform
providers: []                       # subset of [openai, anthropic, azure_openai, bedrock, vertex, self_hosted]
langsmith_target: cloud             # cloud | self_hosted
environments: [local, dev, staging, prod]
slos:
  p95_latency_seconds: 20
cost_budgets:
  max_usd_per_week: 100
governs:
  paths:
    - "deploy/**"
    - "configs/environments/**"
    - ".github/workflows/deploy.yml"
---

# OPS-001 — <Project name> Operations

Records the generation-time choices from agent-forge's copier prompts
(deploy target, providers, LangSmith target) as a governed decision with a
paper trail, per agentic-platform-plan.md §1.6. The runtime reads this spec
directly — it is not just documentation.

## Redaction

Keyed off `DS-` spec `classification` fields automatically. If
`langsmith_target=self_hosted`, traces never leave the VPC and full payloads
are acceptable. If `cloud`, anything above the configured sensitivity
threshold is redacted before the trace leaves.
