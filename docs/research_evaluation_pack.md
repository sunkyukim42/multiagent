# Task 9: Research Evaluation Pack

Task 9 adds an offline research-evaluation scaffold on top of the Task 8
benchmark outputs. It organizes method metadata, synthetic case-set metadata,
ablation definitions, descriptive seed-level aggregation, and KCI-style
Markdown tables.

The pack is illustrative infrastructure. It is not paper-ready, does not make
statistically conclusive claims, and is not financial, procurement, or legal
advice. Heuristic groundedness remains lexical and is not semantic entailment.

## Method Matrix

`configs/research/method_matrix.yaml` lists the methods used for organization:

- `mock_baseline`
- `domain_rag_only`
- `rag_ledger`
- `rag_ledger_guardrails`
- `full_reliability_workflow`

All methods are marked `live_enabled: false`. Placeholder methods are clearly
labeled where no matching live implementation exists.

## Case Sets

`configs/research/case_sets.yaml` defines synthetic case sets for oil,
procurement, and the combined full demo. Sample case sets must use
`synthetic: true` and `paper_ready: false`.

## Ablations

`configs/research/ablation_matrix.yaml` defines descriptive comparisons:

- no-domain vs domain metadata
- RAG vs no RAG
- evidence-ledger effect
- guardrails effect
- workflow effect

The ablation output reports descriptive means and bootstrap intervals when
paired case/seed data exists. Missing paired data is reported as a warning.

## Commands

Run the offline research evaluation and rebuild the configured Task 8 benchmark
pack:

```bash
python scripts/run_research_evaluation.py \
  --config configs/research/task9_research_eval.yaml \
  --output-dir results/research_eval/task9_demo \
  --evaluation-id task9_demo \
  --run-benchmarks
```

Generate KCI-style Markdown tables from an evaluation directory:

```bash
python scripts/generate_kci_tables.py \
  --evaluation-dir results/research_eval/task9_demo \
  --output-dir results/research_tables/task9_demo \
  --table-id task9_demo
```

Generated outputs are ignored under `results/research_eval/` and
`results/research_tables/`.

## Outputs

The research runner writes:

- `research_evaluation_summary.json`
- `method_summary.md`
- `ablation_summary.md`
- `case_set_summary.md`
- `limitations.md`
- `kci_result_tables.md`
- `artifact_manifest.json`
- `run_results.jsonl`

The outputs contain summaries, counts, paths, and aggregate metrics only. They
do not embed full evidence text and do not inspect `.env`.

## Limitations

- Synthetic sample only.
- Not paper-ready.
- Not statistically conclusive.
- No financial, procurement, or legal advice.
- Heuristic groundedness is not semantic entailment.
- Confidence intervals are descriptive bootstrap intervals only.
- Method definitions are metadata for evaluation organization.

Future publication work would require:

- Larger dataset coverage.
- Fixed labels reviewed before evaluation.
- Explicit baselines for every comparison.
- Repeated seeds with preserved seed-level outputs.
- Statistical tests over fixed data and hypotheses.
- Human/expert evaluation where domain judgment is required.
