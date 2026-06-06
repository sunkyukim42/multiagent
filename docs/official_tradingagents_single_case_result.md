# Official TradingAgents Single-Case Execution Artifact

## Scope

This document records one constrained upstream package execution artifact for
TauricResearch/TradingAgents. It is a single case only: `XOM` on
`2020-11-19` at upstream commit
`04f434e86db88e7707bf16db8ed7183f9764fe26`.

The run used a capped configuration with `selected_analysts: market`. It is
not the full upstream default baseline, not the original 2020 `XOM`
reproduction, and not the original existing-model `SELL` baseline
reproduction. It is not paper-ready, not statistically conclusive, makes no
performance claim, and provides no financial/procurement/legal advice.

## Run Summary

| Field | Value |
| --- | --- |
| Run ID | `task17c_official_single_case_20260606T105743Z` |
| Ticker | `XOM` |
| Decision date | `2020-11-19` |
| Upstream repository | `https://github.com/TauricResearch/TradingAgents.git` |
| Upstream commit | `04f434e86db88e7707bf16db8ed7183f9764fe26` |
| Model | `gpt-4.1-mini` |
| Selected analysts | `market` |
| Status | `completed` |
| OpenAI calls | `10 / 10` |
| Input tokens | `36,432` |
| Output tokens | `2,714` |
| Estimated cost | `$0.01891520` |
| Cost cap | `$1.00` |

The cost value is estimate-only, not billing proof.

## Normalized Decision

| Field | Value |
| --- | --- |
| Source kind | `future_official_upstream` |
| Normalized action | `BUY` |
| Normalization status | `success` |
| Raw output path | Ignored generated artifact under `results/official_tradingagents_baseline/` |
| Raw output hash | Present |
| Full raw output in normalized JSON | `false` |

The raw output was not printed, and full raw output text is not embedded in the
normalized JSON.

## Warnings

- The run used `selected_analysts=[market]`, not the full upstream default
  analyst set.
- Historical 2020-only data freeze is not proven.
- A yfinance/current-live cache warning is present:
  `XOM-YFin-data-2021-06-06-2026-06-06.csv`.
- Post-decision leakage status is not determinable from safe metadata.
- The upstream package warned that `gpt-4.1-mini` is outside its known model
  catalog.
- This is a single-case result only.
- Per-run `normalized_decision.jsonl` is absent. The append-only JSONL exists at
  `results/official_baseline_normalization/task17c_single_case/normalized.jsonl`.

## Original-paper boundary

The original paper/presentation reports the proposed oil-domain method as
`BUY` and the existing TradingAgents model as `SELL` for `XOM` on
`2020-11-19`. This constrained upstream package run normalized to `BUY`.

Because this result differs from the reported existing-model `SELL`, this
artifact must not be treated as a completed reproduction of the original
existing-model baseline. Differences may be due to the market-only analyst
subset, current upstream commit, `gpt-4.1-mini`, upstream model catalog
behavior, data/cache behavior, and lack of proven 2020-only data freezing.

The artifact is useful as an execution trace and integration checkpoint, not
as reproduction proof.

## Relationship To Task 16 Prompt-Proxy Pilot

Task 16B was a recent 10-case prompt-proxy pilot. Task 17C is a constrained
official upstream package single-case execution artifact. The two should not
be combined as a direct performance comparison, and both require caveats.

## Artifact Paths

Generated artifacts remain ignored and must not be staged:

- `results/official_tradingagents_baseline/task17c_single_case/task17c_official_single_case_20260606T105743Z/live_run_report.json`
- `results/official_tradingagents_baseline/task17c_single_case/task17c_official_single_case_20260606T105743Z/live_run_report.md`
- `results/official_baseline_normalization/task17c_single_case/task17c_official_single_case_20260606T105743Z/normalized_decision.json`
- `results/official_baseline_normalization/task17c_single_case/normalized.jsonl`

## Safety

Task 17C.5 was a read-only audit. It made no additional OpenAI call, no
provider API call, and no upstream rerun. `.env` was not read or printed. Raw
output was not printed. Generated outputs remain ignored. API keys are not
included. This document provides no advice.
