# Interview Story Bank

## Story 1: Stabilizing The Demo

- Situation: The original live demo path was fragile for offline review.
- Task: Keep the live path separate while making an API-free workflow testable.
- Action: Added smoke checks, preserved `python main.py`, and documented the
  boundary between live and offline paths.
- Result: The repository can demonstrate reliability work without requiring
  secrets or external service calls.
- Technical keywords: API-free smoke tests, live/offline boundary, regression checks.
- What I learned: Stabilization work is strongest when it protects existing
  behavior before adding new package layers.

## Story 2: Debugging Scope Drift

- Situation: New research scaffolds could accidentally touch runtime graph code.
- Task: Keep packaging work separate from live TradingAgents integration.
- Action: Added scope-safety tests that scan protected files and forbidden
  runtime tokens.
- Result: Each package layer can evolve without changing live graph behavior.
- Technical keywords: scope-safety tests, protected paths, dependency guardrails.
- What I learned: Explicit negative checks reduce ambiguity during incremental
  research packaging.

## Story 3: Domain Registry

- Situation: Generic agent outputs were hard to interpret across domains.
- Task: Add structured domain metadata for synthetic oil and procurement cases.
- Action: Built YAML-backed registry loading and validation.
- Result: Cases now carry explicit task and domain context for reproducible
  benchmark runs.
- Technical keywords: YAML schema, domain metadata, reproducible fixtures.
- What I learned: Domain assumptions should be data, not hidden prompt context.

## Story 4: RAG Temporal Filtering

- Situation: Retrieved evidence needed date and domain constraints.
- Task: Make local retrieval useful for offline evaluation.
- Action: Added deterministic local retrieval over sample documents with
  metadata-aware filtering and scoring.
- Result: Evidence candidates can be inspected without external embeddings.
- Technical keywords: local RAG, temporal filtering, metadata scoring.
- What I learned: Retrieval quality depends on traceable filters as much as
  ranking scores.

## Story 5: Ledger And Guardrails

- Situation: Claims needed traceable support and deterministic checks.
- Task: Connect claims to evidence and compute reliability signals.
- Action: Added Evidence Ledger records plus guardrail metrics for support,
  policy, and routing decisions.
- Result: Reports expose why a case reached final report or human review.
- Technical keywords: evidence ledger, groundedness heuristic, policy checks.
- What I learned: Reviewable claim-evidence links make reliability failures
  easier to diagnose.

## Story 6: Workflow Packaging

- Situation: A reliability pipeline needed repeatable end-to-end outputs.
- Task: Package the workflow without making it a production service.
- Action: Added benchmark pack commands, generated reports, ignored output
  directories, and repeatable validation scripts.
- Result: Reviewers can regenerate the same synthetic workflow artifacts.
- Technical keywords: benchmark pack, ignored artifacts, deterministic reports.
- What I learned: A demo is easier to trust when every artifact has a repeatable
  command and a clear storage boundary.

## Story 7: Research Evaluation

- Situation: Portfolio artifacts needed a research-facing interpretation.
- Task: Summarize methods, cases, ablations, and limitations without overclaim.
- Action: Added Task 9 aggregation and KCI-style Markdown tables with explicit
  disclaimers.
- Result: The package has a research scaffold that is useful for planning but
  remains honest about sample size and label limitations.
- Technical keywords: method matrix, ablation table, KCI-style reporting.
- What I learned: Research-facing outputs need limitation language as much as
  metric summaries.

## Boundaries

- Synthetic and illustrative sample only.
- Not paper-ready.
- Not statistically conclusive.
- No financial/procurement/legal advice.
- Heuristic groundedness is not semantic entailment.
