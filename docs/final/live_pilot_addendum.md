# Live Pilot Addendum

## Scope

This addendum links the completed Task 15D.2 and Task 15D.3 recent `XOM`
pilot to the final research and portfolio package. It documents a five-case
recent API pilot only. It is not the original 2020 `XOM` reproduction, not
paper-ready, not statistically conclusive, makes no performance claim, and
provides no financial/procurement/legal advice.

Primary references:

- `docs/live_recent_pilot_results.md`
- `docs/live_10case_pilot_results.md`
- `docs/live_quantitative_experiment.md`

## Validated Path

The pilot validated a narrow live-evaluation path without changing the live
TradingAgents graph:

- Cached and materialized Alpha Vantage snapshots.
- Deterministic 63-day and 126-day outcome labels.
- Guarded OpenAI live runner with explicit call and cost caps.
- Two-method comparison path using `baseline_tradingagents_like` and
  `domain_agent_only`.
- Task 14 summary and KCI-style artifact generation.
- Ignored generated outputs under `results/`, `results/llm_cache/`, and
  `data/live_snapshots/`.

## Descriptive Facts

| Field | Value |
| --- | --- |
| Cases | `5` |
| Methods | `2` |
| Seeds | `1` |
| OpenAI calls | `10` |
| Labels | `10` |
| Missing labels | `0` |
| UNKNOWN labels | `0` |
| BUY labels | `7` |
| HOLD labels | `3` |
| Total tokens | `14,880` |
| Estimated cost | `$0.0081996` |

The cost value is estimate only, not billing proof.

| Method | Runs | 3M accuracy | 6M accuracy |
| --- | ---: | ---: | ---: |
| `baseline_tradingagents_like` | `5` | `0.6` | `0.4` |
| `domain_agent_only` | `5` | `0.8` | `0.2` |

| Horizon | Pairwise comparison | Difference |
| --- | --- | ---: |
| `63d` | `domain_agent_only - baseline_tradingagents_like` | `+0.2` |
| `126d` | `domain_agent_only - baseline_tradingagents_like` | `-0.2` |

## Interpretation

The result is descriptive only. `domain_agent_only` appears higher at the 3M
horizon in this tiny pilot, while `baseline_tradingagents_like` appears higher
at the 126D horizon. The sample is too small for a superiority claim or a
statistical conclusion.

## Safety

- Full prompts are not included.
- Full model-response text is not included.
- API keys are not included.
- Generated outputs are not committed.
- This addendum provides no advice.
- Synthetic and illustrative sample only.
- Not paper-ready.
- Not statistically conclusive.
- No financial/procurement/legal advice.
- Heuristic groundedness is not semantic entailment.

## Next Planned Experiment

`docs/live_larger_experiment_design.md` records the Task 16A plan for a larger
recent `XOM`/`SPY` experiment. That document is planning only and does not
authorize OpenAI calls, provider calls, or performance claims.

## Ten-Case Prompt-Proxy Pilot

`docs/live_10case_pilot_results.md` records the completed Task 16B and Task
16B.3 ten-case recent `XOM` live pilot. The result is descriptive only and
does not change the limitations above.

The documented methods are prompt/input variants. `baseline_tradingagents_like`
is an offline TradingAgents-like prompt proxy and does not execute the official
TauricResearch/TradingAgents graph, CLI, or upstream codebase. It is not the
official TradingAgents baseline result. `domain_agent_only` is a controlled
domain-context prompt variant, not a live modified TradingAgents graph run.

The ten-case result is not the original 2020 `XOM` reproduction and not an
official TradingAgents baseline reproduction. Official upstream reproduction
remains future work requiring pinned upstream code, fixed model/config,
deterministic data policy, explicit call and cost caps, and separate audit.

## Official Baseline Future Work

`docs/official_tradingagents_baseline_reproduction_design.md` records the Task
17A design for a future official TauricResearch/TradingAgents baseline
reproduction. That design is separate from the completed prompt-proxy pilots
and does not claim that the official upstream baseline or original 2020 `XOM`
target has been reproduced.

Task 17B adds local fake-output normalization preflight support for future
official baseline artifacts. It uses synthetic fixtures only, does not clone or
run upstream code, and remains separate from any official baseline reproduction.

`docs/official_tradingagents_upstream_preflight.md` records the Task 17C.0
upstream selection and license-review preflight. It keeps commit/tag selection
and license review pending, does not clone or run upstream code, does not call
live APIs, and does not claim that official baseline reproduction is complete.

`docs/official_tradingagents_single_case_result.md` records the constrained
Task 17C upstream package execution artifact for `XOM` on `2020-11-19`. The
artifact normalized to `BUY`, while the original paper/presentation reported
the existing TradingAgents model as `SELL`; therefore it is not a completed
original baseline reproduction and not performance evidence.

## Task 17C Constrained Upstream Result Boundary

The Task 17C result is a constrained upstream execution artifact for `XOM` on
`2020-11-19`, not a completed reproduction of the original paper baseline. It
used `selected_analysts=[market]`, a market-only analyst subset, and is not
full upstream default baseline. The normalized action was `BUY`, while the
original paper/presentation reported existing-model `SELL` and proposed method
`BUY`; therefore this artifact is not original existing-model SELL baseline
reproduction.

Historical 2020-only data freeze not proven, a current/live yfinance cache
warning was present, and post-decision leakage was not determinable from safe
metadata. The generated artifacts remain ignored, and the package includes no
raw prompts, no raw model responses, no API keys, and no full raw upstream
output. This artifact is descriptive only, not paper-ready, not statistically
conclusive, no performance claim, and no financial/procurement/legal advice.

## Task 18 Controlled Ablation Future Work

`docs/controlled_domain_ablation_design.md` records the Task 18A controlled
domain-on/off ablation design. Any future performance claim would require that
internal controlled comparison, not the Task 16 prompt-proxy pilot or Task 17C
constrained upstream artifact.

`docs/controlled_domain_ablation_pre_live.md` records the Task 18B pre-live
method mapping and dry-run gate. It keeps `domain_off_internal_baseline` and
`domain_on_proposed` as local controlled prompt/input variants, uses no live
OpenAI or provider calls, and makes no performance claim.

## Task 18C Controlled Ablation Result

`docs/controlled_domain_ablation_live_results.md` records the completed Task
18C controlled internal ablation pilot and Task 18D read-only audit. The run
used `10` cases, `2` methods, `5` seeds, and `100` decision rows. The internal
control was `domain_off_internal_baseline` as the `internal_control`; the
proposed variant was `domain_on_proposed` as the `proposed_variant`; and the
controlled difference was
`domain_specific_oil_context`.

In that pilot, `domain_on_proposed` had higher 63d label-match than
`domain_off_internal_baseline`, while 126d label-match was unchanged. The 63d
labels were all `BUY`, so the 63d lift may partly reflect
`domain_on_proposed`'s stronger `BUY` propensity or action-bias alignment rather
than general superiority. The segment-continuation provenance warning remains:
the first full `--fail-fast` attempt left `6` successful rows in cache but no
segment manifest, and two later segment manifests document `94` live OpenAI
calls as `4 + 90`. The final artifact has `100` unique successful decision
rows.

The Task 18C result is descriptive only, not statistically conclusive, no
performance claim, and no financial/procurement/legal advice. It does not
complete official TradingAgents reproduction, official TradingAgents baseline
reproduction, or the original 2020 `XOM` reproduction. Generated artifacts
remain ignored, and no raw prompts, no raw model responses, no model-response
text, no API keys, and no full raw model outputs are included here.
