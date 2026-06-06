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
