# Portfolio Demo

## Setup Assumptions

The offline demo uses local sample documents and claim JSONL files. API keys are not required. Generated artifacts are ignored by git.

## Demo Commands

```bash
python scripts/run_benchmark_pack.py --config configs/benchmarks/task8_full_demo.yaml --output-dir results/benchmark_packs/task8_full_demo --pack-id task8_full_demo --rebuild-index
python scripts/generate_research_report.py --benchmark-dir results/benchmark_packs/task8_full_demo --output-dir results/reports/task8_research --report-id task8_research
python scripts/generate_portfolio_summary.py --benchmark-dir results/benchmark_packs/task8_full_demo --output-dir results/reports/task8_portfolio --report-id task8_portfolio
```

## Expected Outputs

- `benchmark_summary.json` and `benchmark_summary.md`
- `run_summaries.jsonl`
- `artifact_manifest.json`
- `ablation_summary.json` and `ablation_summary.md`
- `research_report.md`
- `portfolio_summary.md`

## Interview Explanation

Frame the project as an AI/AX engineering demo that adds reliability infrastructure around domain-specific agent outputs. Emphasize API-free tests, local reproducibility, evidence traceability, deterministic guardrails, and generated artifact hygiene.

## Boundaries

The demo does not require API keys, does not call live services, does not modify the live TradingAgents graph, and does not provide financial or procurement advice.
