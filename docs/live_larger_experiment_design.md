# Larger Recent API Experiment Design

## Scope

Task 16A is a planning-only design for a larger recent API experiment. It does
not call OpenAI, provider APIs, embeddings, live TradingAgents, or `python
main.py`. It is not the original 2020 `XOM` reproduction, not an official
TradingAgents baseline reproduction, not paper-ready, not statistically
conclusive, makes no performance claim, and provides no
financial/procurement/legal advice.

The Task 16B live run later completed only after a separate preflight, fresh
cache/readiness checks, and this exact approval phrase before live OpenAI:

`I approve up to 20 OpenAI calls and a $1.00 estimated cap for Task 16B`

## Motivation

Task 15D.2 completed a successful five-case descriptive pilot. That pilot
showed that cached/materialized Alpha Vantage snapshots, deterministic labels,
guarded OpenAI calls, and Task 14 summaries can be connected without changing
the live TradingAgents graph.

Task 16A plans a larger but still capped extension. A larger sample is needed
before any research claim could be considered, and even the default 10-case
tier remains exploratory.

## Task 15D.2 Pilot Anchor

The Task 15D.2 five-case recent `XOM` pilot is the descriptive anchor for this
design.

| Task 15D.2 Fact | Value |
| --- | --- |
| Cases | `5` |
| Methods | `2` |
| Seeds | `1` |
| OpenAI calls | `10` |
| Decisions | `10` |
| Labels | `10` |
| Missing labels | `0` |
| UNKNOWN labels | `0` |
| BUY labels | `7` |
| HOLD labels | `3` |
| Total tokens | `14,880` |
| Estimated cost | `$0.0081996` |

| Method | Runs | 3M accuracy | 6M accuracy |
| --- | ---: | ---: | ---: |
| `baseline_tradingagents_like` | `5` | `0.6` | `0.4` |
| `domain_agent_only` | `5` | `0.8` | `0.2` |

| Horizon | Pairwise comparison | Difference |
| --- | --- | ---: |
| `63d` | `domain_agent_only - baseline_tradingagents_like` | `+0.2` |
| `126d` | `domain_agent_only - baseline_tradingagents_like` | `-0.2` |

These values are a descriptive pilot anchor only. The cost is estimate only,
not billing proof. `domain_agent_only` appears higher at 3M, while
`baseline_tradingagents_like` appears higher at 126D. This is not a
performance claim, not statistically conclusive, not paper-ready, and not
financial/procurement/legal advice.

## Task 16B Ten-Case Pilot Result

Task 16B completed the default 10-case tier as a capped descriptive pilot. The
audited result is documented in `docs/live_10case_pilot_results.md`.

| Task 16B Fact | Value |
| --- | --- |
| Cases | `10` |
| Methods | `2` |
| Seeds | `1` |
| OpenAI calls | `20` |
| Failed rows | `0` |
| Labels | `20` |
| Missing labels | `0` |
| UNKNOWN labels | `0` |
| BUY labels | `14` |
| HOLD labels | `6` |
| Total tokens | `30,755` |
| Estimated cost | `$0.0168728` |

| Prompt variant | Method ID | 3M accuracy | 126D accuracy |
| --- | --- | ---: | ---: |
| Baseline TradingAgents-like prompt proxy | `baseline_tradingagents_like` | `0.8` | `0.2` |
| Domain-context prompt variant | `domain_agent_only` | `0.8` | `0.2` |

The pairwise differences were `0.0` at both 63d and 126d. These values are
descriptive only. `baseline_tradingagents_like` is an offline prompt proxy and
does not execute the official TauricResearch/TradingAgents graph, CLI, or
upstream codebase. `domain_agent_only` is a controlled prompt/input variant,
not a live modified TradingAgents graph execution. Task 16B is not an official
TradingAgents baseline reproduction and not the original 2020 `XOM`
reproduction.

## Task 17A Official Baseline Design

`docs/official_tradingagents_baseline_reproduction_design.md` records the Task
17A plan for a future official TauricResearch/TradingAgents baseline
reproduction. It keeps the Task 16B prompt-proxy pilot separate from both the
future upstream baseline and the original 2020 `XOM` reproduction target. Task
17A is design only and does not authorize cloning upstream code, live OpenAI
calls, provider calls, or performance claims.

## Task 18A Controlled Ablation Design

`docs/controlled_domain_ablation_design.md` records the future controlled
domain-on/off ablation path. That design keeps the primary comparison inside
the same local runner: `domain_on_proposed` versus
`domain_off_internal_baseline`. It treats official upstream TradingAgents as a
caveated external reference, not the primary performance comparison.

## Candidate Design

- Base ticker: `XOM`.
- Benchmark ticker: `SPY`.
- Data source: recent Alpha Vantage compact availability, with no provider
  calls in Task 16A.
- Default next tier: 10 recent cases.
- Future-only tier: 20 recent cases, requiring separate approval.
- Horizons: 63 and 126 trading days.

Candidate dates should be selected only where both `XOM` and `SPY` have an
entry row plus 63-day and 126-day future rows. Dates should be spread across
the eligible compact window and should avoid over-concentrating adjacent
trading days. Cached and materialized Alpha Vantage raw data should be reused
where possible.

## Methods

Task 16B used the same two controlled method IDs from the recent pilot:

- `baseline_tradingagents_like`
- `domain_agent_only`

Potential later methods are `domain_rag` and `rag_ledger`, but those should not
be added until the prompt-proxy boundary is preserved and a larger design is
separately approved.

## Run And Cost Plan

| Tier | Cases | Methods | Seeds | Max OpenAI Calls | Cost Cap |
| --- | ---: | ---: | ---: | ---: | ---: |
| `ten_case_two_method` | `10` | `2` | `1` | `20` | `$1.00` |
| `twenty_case_two_method` | `20` | `2` | `1` | `40` | Separate approval |

The 20-call estimate is roughly double the Task 15D.2 10-call baseline under
similar prompts. The estimate is for planning only and may differ from billing.
Multi-seed runs should wait until case-level stability is verified.

## Data And Cache Plan

Provider collection and OpenAI evaluation should remain separate steps. Task
16B must use the Alpha Vantage shared raw/materialization path from Task
15D.1a, run cache-first where possible, and prove snapshot readiness before
OpenAI is enabled.

Before any live OpenAI run:

- All cases must inspect as `ready_for_labeling`.
- Deterministic labels must have `missing=0` and `UNKNOWN=0`.
- Label windows and future rows must remain excluded from prompt context.
- Generated outputs must stay under ignored `results/`, `results/llm_cache/`,
  and `data/live_snapshots/` paths.

## Statistical Plan

Task 16B should reuse the Task 14 summary path: descriptive method metrics,
pairwise comparisons, bootstrap confidence intervals, McNemar artifacts,
Wilcoxon artifacts, and KCI-style tables. At 10 cases, the experiment is still
likely underpowered. Effect sizes and confidence intervals should be reported
as exploratory, and no statistical claim should be made unless sample size and
test assumptions support it.

## Go/No-Go Gates

- Source tree clean.
- 10 cases generated.
- 10/10 cases inspect as `ready_for_labeling`.
- Labels report `20` labels, `missing=0`, and `UNKNOWN=0`.
- Dry run reports `planned=20`, `openai_calls=0`, and `failed=0`.
- Estimated cost is below the configured cap.
- User provides the exact Task 16B approval phrase before live OpenAI.

## Risks

- Provider rate limits can block future cache refreshes.
- Alpha Vantage compact historical availability can shift over time.
- Adjacent recent dates may not be independent.
- A 10-case sample remains small.
- Cost estimates can differ from billing.
- Model outputs may vary across calls.
- The design is not evidence of investment usefulness.
