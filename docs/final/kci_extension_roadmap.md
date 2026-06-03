# KCI Extension Roadmap

## Current Position

The current package is a reproducible offline scaffold for synthetic oil and
procurement cases. It is useful for planning a study, but it is not a finished
paper package.

## Dataset Expansion

- Expand beyond the tiny synthetic sample.
- Add fixed case labels prepared before model or workflow comparison.
- Separate train-like development cases from held-out evaluation cases.
- Track domain, task type, decision date, and evidence-source metadata.

## Baseline Matrix

- Compare no-RAG, RAG-only, ledger-only, guardrails-only, workflow-only, and
  full reliability workflow methods.
- Keep all methods offline for the first controlled study.
- Add live API-backed baselines only after review approval and secret handling
  are documented outside this package.

## Ablation And Metrics

- Preserve component-changed ablation metadata.
- Track citation coverage, temporal leakage, grounded claim rate, unsupported
  claim rate, policy compliance, route counts, and review routes.
- Treat heuristic groundedness as a lexical signal rather than semantic
  entailment.

## Statistical Plan

- Use repeated seeds only after the dataset is large enough.
- Run statistical tests only after fixed labels and baseline definitions are
  stable.
- Report uncertainty without claiming more than the sample can support.

## Contribution

The intended contribution is a reliability-aware evaluation framework for
domain-specific decision agents, centered on evidence traceability, route
transparency, and reviewable limitations.

## Risks And Timeline

- Risk: labels may be expensive to produce consistently.
- Risk: route decisions may need domain expert calibration.
- Month 1: dataset and fixed-label design.
- Month 2: baseline and ablation matrix.
- Month 3: repeated runs, analysis, and human/expert review.

## Boundaries

- Synthetic and illustrative sample only.
- Not paper-ready.
- Not statistically conclusive.
- No financial/procurement/legal advice.
- Heuristic groundedness is not semantic entailment.
