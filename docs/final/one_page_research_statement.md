# One-Page Research Statement

## Motivation

Enterprise decision agents can produce useful summaries only when their domain
context, evidence links, and reliability checks are visible. This project asks
how an offline reliability-aware multi-agent RAG pipeline can make synthetic
oil and procurement decisions easier to inspect before any production use.

## Problem

The baseline problem is not model quality alone. The harder research problem is
whether claims, evidence, route decisions, and limitations can be represented in
a reproducible package that supports review by engineers and domain experts.

## Contribution

The implemented package separates the live TradingAgents path from an offline
research scaffold. It adds a Domain Registry, local RAG retrieval, Evidence
Ledger records, deterministic Reliability Guardrails, workflow routing,
benchmark reports, KCI-style tables, and final presentation documents.
The final package also includes a descriptive live-pilot addendum that records
an audited recent XOM pilot without making a performance claim.

## Next Questions

- How much do fixed expert labels change groundedness and policy metrics?
- Which baselines should be compared when dataset size is large enough?
- Which routing failures are best handled by retry, stop, or human review?
- What reviewer interface would make evidence inspection faster and clearer?

## Limitations And Future Work

- Synthetic and illustrative sample only.
- Not paper-ready.
- Not statistically conclusive.
- No financial/procurement/legal advice.
- Heuristic groundedness is not semantic entailment.
- Future work needs larger datasets, fixed labels, explicit baselines, repeated
  seeds, statistical tests, and human/expert evaluation.
