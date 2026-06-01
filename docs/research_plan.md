# Research Plan

## Motivation

The original TradingAgents workflow is useful for demonstrating multi-agent financial analysis, but the local project started with a narrow live demo centered on one domain, one stock, and one date. The research extension explores how domain-specific metadata, offline retrieval, evidence records, and deterministic reliability checks can make multi-agent outputs easier to audit.

## Research Direction

The proposed direction is a reliability-aware domain-specific multi-agent RAG system. The offline package supports oil and procurement sample cases with local synthetic documents, structured claims, evidence links, and reliability metrics.

## Research Questions

| ID | Question |
| --- | --- |
| RQ1 | How does domain-specific evidence affect the traceability of multi-agent decisions? |
| RQ2 | Which deterministic reliability metrics are useful for identifying weak or risky outputs? |
| RQ3 | Can reliability metrics support deterministic routing to final report, retry, human review, or stop? |

## Planned Evaluation Design

The current Task 8 benchmark pack is illustrative. A research-grade evaluation would require larger curated datasets, fixed labels, explicit baseline methods, repeatable retrieval settings, and statistical tests after enough cases are collected.

## Limitations

Sample outputs are synthetic and not paper-ready benchmarks. Heuristic groundedness is lexical overlap, not semantic entailment. Reports are not investment advice, procurement advice, legal advice, or operational approval.
