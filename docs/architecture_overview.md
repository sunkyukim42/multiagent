# Architecture Overview

This project extends TradingAgents into an offline reliability-aware domain-specific multi-agent RAG research system.

## Pipeline

Domain Registry -> Experiment Runner -> Local RAG -> Evidence Ledger -> Reliability Guardrails -> Reliability Workflow -> Reporting.

## Module Map

| Stage | Main package | Purpose |
| --- | --- | --- |
| Domain Registry | `enterprise_decision_agents.core` | Load YAML domain metadata and masked environment status. |
| Experiment Runner | `enterprise_decision_agents.evaluation` | Run API-free mock cases, methods, and seeds. |
| Local RAG | `enterprise_decision_agents.ingestion`, `enterprise_decision_agents.retrieval` | Build local chunk indexes and retrieve metadata-aware candidates. |
| Evidence Ledger | `enterprise_decision_agents.core`, `enterprise_decision_agents.storage` | Store claims, evidence records, and links. |
| Guardrails | `enterprise_decision_agents.guardrails` | Compute deterministic reliability metrics. |
| Workflow | `enterprise_decision_agents.orchestration` | Route offline runs to final report, retry, human review, or stop. |
| Reporting | `enterprise_decision_agents.reporting` | Package workflow outputs into benchmark, research, and portfolio summaries. |

## Data Flow

Synthetic sample documents are indexed locally under `data/indexes/`. Structured sample claims are linked to retrieved chunks in Evidence Ledgers under `results/ledgers/`. Reliability reports are written under `results/reliability/` or workflow attempt folders. Workflow artifacts are written under `results/workflows/`. Task 8 benchmark and report outputs are written under `results/benchmark_packs/` and `results/reports/`.

## Offline Vs Live

The Task 8 package is offline. It does not call external APIs, OpenAI, embeddings, or live TradingAgents graph code. The original `python main.py` path remains available separately for live demos when API keys are configured.

## Not Implemented

Task 8 does not add a dashboard, production server, auth, human approval UI, vector database, RAGAS/TruLens evaluation, PDF export, PowerPoint export, live graph integration, or financial/procurement advice.
