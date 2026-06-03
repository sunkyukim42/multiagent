# Portfolio Project Summary

## Problem

Enterprise AI and AX workflows need more than fluent text. They need domain
configuration, inspectable evidence, reliability metrics, and deterministic
routing before a decision-support output can be reviewed with confidence.

## AI/AX Relevance

The project demonstrates how an agent workflow can become auditable without
depending on a live API demo. It packages synthetic decision cases, local
retrieval, evidence ledgers, guardrails, and route decisions into repeatable
command-line artifacts.

## Architecture

The offline path is Domain Registry -> Experiment Runner -> Local RAG ->
Evidence Ledger -> Reliability Guardrails -> Reliability Workflow -> Reporting
-> Research Tables -> Final Package. The live `python main.py` demo remains a
separate path for configured API-backed use.

## Reliability And Reproducibility

- Domain metadata constrains case interpretation.
- Local retrieval uses sample documents and deterministic scoring.
- Evidence records connect claims to retrieved support.
- Guardrails compute lexical and policy-oriented reliability metrics.
- Workflow routing records final report and human review decisions.
- Benchmark, research, and final-package commands regenerate ignored outputs.

## Demo Commands

```bash
python scripts/run_benchmark_pack.py --config configs/benchmarks/task8_full_demo.yaml --output-dir results/benchmark_packs/task10_regression_full_demo --pack-id task10_regression_full_demo --rebuild-index
python scripts/run_research_evaluation.py --config configs/research/task9_research_eval.yaml --output-dir results/research_eval/task10_regression_eval --evaluation-id task10_regression_eval --run-benchmarks
python scripts/generate_kci_tables.py --evaluation-dir results/research_eval/task10_regression_eval --output-dir results/research_tables/task10_regression_eval --table-id task10_regression_eval
python scripts/generate_final_package.py --config configs/presentation/final_portfolio_package.yaml --output-dir results/final_packages/task10_final_package --package-id task10_final_package
```

## Engineering Practices

- API-free tests and smoke checks.
- Secret-safe schema validation.
- Generated artifacts ignored by git.
- Deterministic Markdown and JSON outputs.
- Scope-safety tests around live graph and dependency boundaries.

## Limitations

- Synthetic and illustrative sample only.
- Not paper-ready.
- Not statistically conclusive.
- No financial/procurement/legal advice.
- Heuristic groundedness is not semantic entailment.
