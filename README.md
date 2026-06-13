# Reliability-Aware Domain-Specific Multi-Agent RAG System

This repository contains a research prototype for **domain-specific multi-agent RAG with evidence traceability and reliability checks**.

The project extends a TradingAgents-style financial analysis workflow with a separate offline research layer for:

- domain-aware evidence retrieval,
- claim-evidence linking,
- deterministic reliability checks,
- controlled evaluation scaffolding,
- conservative reporting and portfolio packaging.

The default repository workflow is **offline-first**. It does not require API keys and does not call OpenAI, provider APIs, live TradingAgents, LLMs, or embedding services.

The original live `python main.py` TradingAgents path remains separate.

---

## 1. Current Status

The repository currently includes:

- offline benchmark and report generation,
- local RAG over sample documents,
- Evidence Ledger and Reliability Guardrails,
- optional offline reliability workflow,
- live-evaluation scaffolding with explicit safety gates,
- controlled domain-on/off ablation documentation,
- final portfolio package documentation,
- final release note.

The accepted final package is documented in:

- `docs/final/final_release_note.md`

The controlled ablation result is documented in:

- `docs/controlled_domain_ablation_live_results.md`

These materials are descriptive research artifacts. They are **not** performance claims, not statistically conclusive, and not financial, procurement, or legal advice.

---

## 2. Quickstart: Offline Demo

Run the full offline benchmark pack:

```bash
python scripts/run_benchmark_pack.py \
  --config configs/benchmarks/task8_full_demo.yaml \
  --output-dir results/benchmark_packs/task8_full_demo \
  --pack-id task8_full_demo \
  --rebuild-index
```

Generate a research-oriented Markdown report:

```bash
python scripts/generate_research_report.py \
  --benchmark-dir results/benchmark_packs/task8_full_demo \
  --output-dir results/reports/task8_research \
  --report-id task8_research
```

Generate a portfolio-oriented Markdown summary:

```bash
python scripts/generate_portfolio_summary.py \
  --benchmark-dir results/benchmark_packs/task8_full_demo \
  --output-dir results/reports/task8_portfolio \
  --report-id task8_portfolio
```

Generated artifacts are ignored under `results/` and `data/indexes/`.

---

## 3. Validation

Run the standard offline validation suite:

```bash
python -m compileall tradingagents enterprise_decision_agents tests scripts
pytest
python scripts/smoke_test.py
python scripts/validate_domains.py
python scripts/validate_domains.py --check-env
```

`validate_domains.py --check-env` reports only `present` or `missing` status and must not print secret values.

---

## 4. Final Package

Generate the final portfolio package:

```bash
python scripts/generate_final_package.py \
  --config configs/presentation/final_portfolio_package.yaml \
  --output-dir results/final_packages/task18f_final_package_refresh_rerun \
  --package-id task18f_final_package_refresh_rerun
```

The final package is generated under an ignored `results/` path. It includes tracked Markdown artifacts and source references for the live-pilot and ablation documentation.

Primary final-package documentation:

- `docs/final/final_release_note.md`
- `docs/final/portfolio_project_summary.md`
- `docs/final/live_pilot_addendum.md`
- `docs/final/project_limitations.md`
- `docs/controlled_domain_ablation_live_results.md`
- `docs/official_tradingagents_single_case_result.md`

---

## 5. Repository Map

| Path | Purpose |
| --- | --- |
| `tradingagents/` | Original/live TradingAgents implementation and graph. |
| `enterprise_decision_agents/core/` | Domain metadata, run context, claims, and evidence schemas. |
| `enterprise_decision_agents/evaluation/` | API-free experiment runner and metrics. |
| `enterprise_decision_agents/ingestion/` | Offline document parsing and chunking. |
| `enterprise_decision_agents/retrieval/` | Local RAG index and hybrid retrieval. |
| `enterprise_decision_agents/storage/` | Evidence Ledger persistence. |
| `enterprise_decision_agents/guardrails/` | Deterministic Reliability Guardrails. |
| `enterprise_decision_agents/orchestration/` | Optional offline reliability workflow. |
| `enterprise_decision_agents/reporting/` | Benchmark, research, and portfolio reporting. |
| `enterprise_decision_agents/presentation/` | Final-package schemas and builder. |
| `enterprise_decision_agents/live/` | Live case-set, snapshot, prompt, LLM-output, and summary scaffolding. |
| `configs/` | Domain, RAG, ledger, guardrail, workflow, experiment, benchmark, and live YAML configs. |
| `configs/presentation/` | Final package presentation config. |
| `configs/live_experiments/` | Live case panels, provider limits, labeling, prompt, and evaluation configs. |
| `data/` | Synthetic cases, sample claims, local RAG sample documents, and generated case panels. |
| `docs/` | Architecture, research plan, experiment notes, final docs, and release notes. |
| `scripts/` | Offline build, validation, benchmark, report, workflow, final package, and live-evaluation commands. |
| `tests/` | Unit, regression, safety, and documentation tests. |

---

## 6. Main Workflows

### 6.1 Offline Reliability Workflow

The offline workflow links local RAG, Evidence Ledger, and Reliability Guardrails.

Typical stages:

1. build or reuse a local RAG index,
2. retrieve evidence candidates,
3. build an Evidence Ledger,
4. run deterministic guardrails,
5. route the result to final report, retry, human review, or stop.

These commands use local files only and do not call live services.

### 6.2 Live Experiment Scaffolding

Live experiment tooling is provided for controlled research evaluation, but it is not the default path.

The live scaffolding includes:

- deterministic live case-set building,
- cache-first provider snapshot planning,
- cache-only market outcome labeling,
- prompt context preview,
- gated OpenAI runner abstraction,
- batch live research evaluation,
- offline experiment summary and KCI-style tables.

Live provider collection and live OpenAI execution require explicit flags, local keys, call caps, cost caps, and separate approval.

### 6.3 Controlled Domain Ablation

The controlled ablation compares:

- `domain_off_internal_baseline`
- `domain_on_proposed`

The intended controlled difference is `domain_specific_oil_context`.

The documented pilot found higher 63-day label-match for the domain-on condition and unchanged 126-day label-match. Because all 63-day labels were `BUY`, this result may partly reflect BUY propensity and label-base-rate alignment. It is treated as exploratory only.

---

## 7. Documentation

Recommended reading order:

1. [Final Release Note](docs/final/final_release_note.md)
2. [Portfolio Project Summary](docs/final/portfolio_project_summary.md)
3. [Project Limitations](docs/final/project_limitations.md)
4. [Live Pilot Addendum](docs/final/live_pilot_addendum.md)
5. [Controlled Domain Ablation Live Results](docs/controlled_domain_ablation_live_results.md)
6. [Official TradingAgents Single-Case Result](docs/official_tradingagents_single_case_result.md)
7. [Architecture Overview](docs/architecture_overview.md)
8. [Research Plan](docs/research_plan.md)
9. [Evaluation Metrics](docs/evaluation_metrics.md)
10. [Release Checklist](docs/release_checklist.md)

---

## 8. Safety Boundaries

- Offline commands do not require API keys.
- `.env` is ignored by git and should contain local secrets only.
- Do not print `.env` or API key values.
- Generated outputs are ignored under `results/`, `data/indexes/`, `data/live_snapshots/`, and related experiment output paths.
- `python main.py` is the separate live TradingAgents demo path.
- Raw prompts and raw model outputs should not be committed.
- Sample outputs are synthetic or limited research artifacts unless explicitly documented otherwise.
- Results are not paper-ready unless a specific paper-ready audit says so.
- Results are not statistically conclusive unless explicitly supported by adequate evaluation.
- Reports are not financial, procurement, or legal advice.
- Heuristic groundedness is not semantic entailment.
- The controlled ablation result is descriptive only and should not be stated as a performance proof.
- The constrained official upstream single-case run is not a completed reproduction of the original 2020 XOM baseline.

---

## 9. Development Milestones

| Stage | Summary |
| --- | --- |
| Tasks 1-3 | Stabilized API-free checks, Domain Registry, and mock experiment runner. |
| Tasks 4-7 | Added local RAG, Evidence Ledger, Reliability Guardrails, and offline workflow. |
| Tasks 8-10 | Added benchmark packs, research tables, and final portfolio packaging. |
| Tasks 11-14 | Added live case scaffolding, labeling, prompt construction, gated LLM outputs, and offline summary. |
| Tasks 15-17 | Prepared recent XOM pilots and constrained official TradingAgents upstream checks. |
| Task 18 | Designed, ran, audited, documented, and packaged a controlled domain-on/off ablation pilot. |

Detailed task-level notes are retained in documentation and tests. The README intentionally keeps only the high-level progression.

---

## 10. Legacy TradingAgents Demo

The original live demo path is still available:

```bash
python main.py
```

Use it only when the required local API keys are configured in `.env`.

For legacy prompt-file and API I/O notes, prefer a separate local document such as:

```text
docs/legacy_tradingagents_notes.md
```

Do not keep long prompt-path lists, API I/O dumps, or local operational notes at the top of this README.

---

## 11. What This Repository Does Not Claim

This repository does not claim:

- statistically significant performance improvement,
- investment usefulness,
- financial, procurement, or legal advice,
- production deployment readiness,
- official TradingAgents baseline reproduction,
- original 2020 XOM reproduction,
- superiority of the proposed method over all baselines.

The main contribution is a research system for making domain-specific multi-agent outputs easier to trace, inspect, and evaluate.
