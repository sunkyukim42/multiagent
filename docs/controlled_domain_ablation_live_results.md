# Controlled Domain-On/Off Ablation Live Pilot Results

## Scope

This document records the Task 18C controlled internal ablation pilot and the
Task 18D read-only audit. The pilot used `10` recent `XOM` cases, `2` methods,
`5` seeds, and `100` decision rows.

`domain_off_internal_baseline` is the internal control. `domain_on_proposed` is
the proposed variant. The controlled difference is
`domain_specific_oil_context`.

This result is descriptive only, not statistically conclusive, not paper-ready,
and makes no performance claim. It provides no financial/procurement/legal
advice. It is not an official TradingAgents baseline reproduction and not the
original 2020 `XOM` reproduction.

## Run Summary

| Field | Value |
| --- | --- |
| Run ID | `task18c_controlled_ablation_live` |
| Decisions | `100` |
| Methods | `2` |
| Cases | `10` |
| Seeds | `5` |
| Final artifact planned / completed | `100 / 100` |
| Final artifact failed / skipped | `0 / 0` |
| Final artifact mode | `cache_only` |
| Final artifact cache hits | `100` |
| Final artifact OpenAI calls | `0` |
| Actual live cache rows | `100` successful outputs |
| Input tokens | `137,430` |
| Output tokens | `18,238` |
| Total tokens | `155,668` |
| Estimated cost | `$0.08415280` |
| Cost cap | `$5.00` |

The cost is estimate-only, not billing proof. Generated artifacts are ignored.

## Method Definitions

| Method | Role | Domain context | Disabled features |
| --- | --- | --- | --- |
| `domain_off_internal_baseline` | `internal_control` | `domain_enabled=false` | RAG, ledger, guardrails, workflow, and live TradingAgents graph. |
| `domain_on_proposed` | `proposed_variant` | `domain_enabled=true` | RAG, ledger, guardrails, workflow, and live TradingAgents graph. |

Both methods used the same local runner, cases, labels, snapshots, parser,
model, cost cap, call cap, and seed set. Official upstream TradingAgents remains
an external and caveated reference.

## All-Run Metrics

| Method | Runs | Actions | 63d label-match | 126d label-match | Cost | Tokens |
| --- | ---: | --- | ---: | ---: | ---: | --- |
| `domain_off_internal_baseline` | `50` | `BUY=19`, `HOLD=31` | `19/50 = 0.38` | `11/50 = 0.22` | `$0.03968480` | `65,340 input / 8,468 output / 73,808 total` |
| `domain_on_proposed` | `50` | `BUY=37`, `HOLD=13` | `37/50 = 0.74` | `11/50 = 0.22` | `$0.04446800` | `72,090 input / 9,770 output / 81,860 total` |

Pairwise descriptive difference:

| Horizon | Difference |
| --- | ---: |
| `63d` | `+0.36` |
| `126d` | `0.0` |

## Majority And Stability Metrics

| Method | 63d majority-vote | 126d majority-vote | Mean stability |
| --- | ---: | ---: | ---: |
| `domain_off_internal_baseline` | `4/10 = 0.40` | `2/10 = 0.20` | `0.90` |
| `domain_on_proposed` | `8/10 = 0.80` | `2/10 = 0.20` | `0.94` |

There were `0` ties. Majority action differs in `4/10` cases.

| Horizon | Domain-on improves | Domain-on worsens | Unchanged |
| --- | ---: | ---: | ---: |
| `63d` | `4` | `0` | `6` |
| `126d` | `2` | `2` | `6` |

Repeated seeds must not be treated as independent cases without caveat.

## Label-Base-Rate Caveat

The Task 18D label audit confirmed that all `10` 63-day labels are `BUY`. The
126-day labels are mixed: `BUY=4`, `HOLD=6`.

The 63d lift may partly reflect `domain_on_proposed` having a stronger `BUY`
propensity in a panel where all 63d labels are `BUY`. `domain_on_proposed`
chose `BUY` more often than `domain_off_internal_baseline`: `37/50` all-run
actions versus `19/50`. The 126d horizon did not improve. Therefore the result
is horizon-specific and may reflect action-bias alignment, not general
superiority.

## Segment-Continuation Provenance Warning

The first full `--fail-fast` attempt stopped after a transient/error status.
That first attempt left `6` successful rows in cache but no segment manifest.
Two later segment manifests document `94` live OpenAI calls: `4 + 90`.

The final materialized artifact contains `100` unique successful decision rows
with no missing case/method/seed combinations. The transient/error attempt is
not represented in final decisions and is not documented in final manifest or
run-report warnings.

This does not change the final coverage or recomputed metrics, but it is a
provenance/accounting caveat.

## Task 14 And KCI Summary

The Task 14-style summary contains `100` decisions, `2` methods, and `2`
pairwise rows. Method metrics and pairwise differences match recomputation.
Statistical artifacts include small-sample and not-statistically-conclusive
warnings. KCI tables include no-advice and not-statistically-conclusive wording.

No superiority or performance claim is made.

## Interpretation

In this controlled pilot, `domain_on_proposed` had higher 63d label-match than
`domain_off_internal_baseline`. The 126d label-match was unchanged.

This is descriptive controlled-ablation evidence only. It is not proof, not
statistically conclusive, not paper-ready, and not investment/procurement/legal
advice. Repeated runs must not be treated as independent cases without caveat.

Official upstream TradingAgents remains a caveated external reference. The Task
17C constrained upstream artifact and the original 2020 `XOM` reproduction
remain separate.

## Artifact Paths

The generated artifacts remain ignored:

- `results/live_research_eval/task18c_controlled_ablation_live/`
- `results/llm_cache/task18c_controlled_ablation_live/`
- `results/live_experiment_summary/task18c_controlled_ablation_live/`
- `results/live_kci_tables/task18c_controlled_ablation_live/`

This document references paths only. It does not embed raw generated content.

## Safety

- No additional OpenAI/provider calls were made during the Task 18D audit.
- `.env` was not read or printed.
- Raw prompts were not printed.
- Raw LLM responses were not printed.
- Raw model outputs exist only in ignored LLM artifacts.
- Generated outputs remain ignored.
- Secret-like findings: `0`.
- Affirmative overclaim findings: `0`.
- False reproduction findings: `0`.
- No advice.
