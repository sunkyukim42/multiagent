# Architecture Overview

This repository extends TradingAgents into an offline, reliability-aware,
domain-specific multi-agent RAG research system.

## Pipeline

```text
Domain Registry
  -> Experiment Runner
  -> Local RAG
  -> Evidence Ledger
  -> Reliability Guardrails
  -> Reliability Workflow
  -> Reporting
```

## Module Map

| Stage | Main package | Purpose |
| --- | --- | --- |
| Domain Registry | `enterprise_decision_agents.core` | Load domain metadata and masked env status. |
| Experiment Runner | `enterprise_decision_agents.evaluation` | Run API-free mock cases and methods. |
| Local RAG | `ingestion`, `retrieval` | Build and query local chunk indexes. |
| Evidence Ledger | `core`, `storage` | Store claims, evidence, and links. |
| Guardrails | `enterprise_decision_agents.guardrails` | Compute reliability metrics. |
| Workflow | `enterprise_decision_agents.orchestration` | Route offline runs by reliability status. |
| Reporting | `enterprise_decision_agents.reporting` | Package benchmark and portfolio outputs. |

## Data Flow

Synthetic sample documents are indexed locally under `data/indexes/`.
Structured sample claims are linked to retrieved chunks in Evidence Ledgers
under `results/ledgers/`.

Reliability reports are written under `results/reliability/` or workflow
attempt folders. Workflow artifacts are written under `results/workflows/`.
Task 8 benchmark and report outputs are written under:

- `results/benchmark_packs/`
- `results/reports/`

## Offline Vs Live

The Task 8 package is offline. It does not call external APIs, OpenAI,
embedding services, or live TradingAgents graph code.

The original `python main.py` path remains separate for live demos when API
keys are configured by the user.

## Not Implemented

Task 8 does not add:

- dashboard or web UI
- production server or auth
- human approval UI
- vector database
- RAGAS or TruLens evaluation
- PDF or PowerPoint export
- live graph integration
- financial, procurement, or legal advice
