# Final Demo Checklist

## Before The Demo

- Confirm `.env` remains ignored by git and do not print its contents.
- Confirm generated outputs stay under ignored `results/` paths.
- Confirm no runtime graph or `main.py` changes are part of the package.
- Confirm the demo uses a no API key required offline path.
- Confirm no generated outputs are staged.
- Confirm the demo uses offline commands only.

## Commands

```bash
python -m compileall tradingagents enterprise_decision_agents tests scripts
pytest
python scripts/smoke_test.py
python scripts/validate_domains.py
python scripts/validate_domains.py --check-env
python scripts/run_benchmark_pack.py --config configs/benchmarks/task8_full_demo.yaml --output-dir results/benchmark_packs/task10_regression_full_demo --pack-id task10_regression_full_demo --rebuild-index
python scripts/run_research_evaluation.py --config configs/research/task9_research_eval.yaml --output-dir results/research_eval/task10_regression_eval --evaluation-id task10_regression_eval --run-benchmarks
python scripts/generate_kci_tables.py --evaluation-dir results/research_eval/task10_regression_eval --output-dir results/research_tables/task10_regression_eval --table-id task10_regression_eval
python scripts/generate_final_package.py --config configs/presentation/final_portfolio_package.yaml --output-dir results/final_packages/task10_final_package --package-id task10_final_package
```

## Review Points

- Benchmark summary exists.
- Research evaluation summary exists.
- KCI-style tables exist.
- Final package summary, manifest, and README exist.
- Required disclaimers appear in generated Markdown.
- No raw secret-like patterns appear in generated artifacts.
- No generated outputs are staged.
- Do not overclaim results during narration.

## Boundaries

- Synthetic and illustrative sample only.
- Not paper-ready.
- Not statistically conclusive.
- No financial/procurement/legal advice.
- Heuristic groundedness is not semantic entailment.
