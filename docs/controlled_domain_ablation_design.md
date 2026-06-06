# Controlled Domain-On/Off Ablation Design

## Scope

Task 18A is design-only. It does not call OpenAI, provider APIs, upstream
TauricResearch/TradingAgents, live TradingAgents, `python main.py`, or any live
experiment runner. It is not the original 2020 `XOM` reproduction, not an
official TradingAgents baseline reproduction, not paper-ready, not
statistically conclusive, makes no performance claim, and provides no
financial/procurement/legal advice.

The future controlled ablation is intended to compare domain-specific context
inside the same local research pipeline. It should use the same repository,
runner, labels, snapshots, model, parser, call caps, cost caps, cases, and
aggregation policy across methods.

## Motivation

Selecting one favorable run from repeated stochastic outputs is not valid
evidence. Same-date LLM outputs can vary because of model stochasticity,
tool/data variation, prompt sensitivity, cache behavior, and live-data
behavior. Future claims should use pre-registered run rules, repeated seeds,
all-run reporting, majority or aggregate rules, and explicit failed-run
reporting.

The strongest future evidence, if later supported, should come from an internal
domain-on versus domain-off ablation under identical conditions. Official
upstream TradingAgents remains an external reference, not the cleanest primary
comparison, because codebase, configuration, prompt, tool, cache, and
data-source differences are confounds.

Task 17C produced a constrained upstream artifact for `XOM` on `2020-11-19`
that normalized to `BUY`. The original paper/presentation reports proposed
oil-domain method `BUY` and existing TradingAgents model `SELL` for that same
date. Because Task 17C differs from the reported existing-model `SELL`, it must
not be used as proof of original baseline reproduction.

## Method Arms

| Arm | Role | Claim policy |
| --- | --- | --- |
| `official_upstream_reference` | Future external reference only | Caveated context only; not the primary controlled claim source. |
| `domain_off_internal_baseline` | Internal control | Same local runner/cases/labels/snapshots/model/parser/caps with domain-specific oil context disabled. |
| `domain_on_proposed` | Proposed internal variant | Same as `domain_off_internal_baseline`, except domain-specific oil context is enabled. |

The primary comparison is `domain_on_proposed - domain_off_internal_baseline`.
The controlled difference is `domain_specific_oil_context`. Any
`official_upstream_reference` comparison is contextual and caveated, not the
primary claim source.

## Primary Claim Policy

Primary future performance evidence, if later supported, should be based on
`domain_on_proposed` versus `domain_off_internal_baseline`. No single-case
result can establish performance. No cherry-picking of repeated runs is
allowed, and all valid runs must be reported. Failed runs must be reported, not
silently dropped.

Any claim must remain descriptive and exploratory unless sample size, controls,
statistical assumptions, and audit evidence are adequate. If `domain_on` appears
higher than `domain_off`, it should be described as controlled exploratory
evidence, not proof. If results are mixed, report mixed results. If repeated-run
instability is high, emphasize instability. No claim should be based on selecting
a favorable run among repeats.

## Experimental Tiers

| Tier | Cases | Methods | Repeats per case-method | Planned OpenAI calls | Cost cap | Purpose |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Tier 1 small controlled ablation pilot | `10` | `2` | `5` | `100` | `$5.00` | Stability and effect-direction estimate only. |
| Tier 2 expanded controlled ablation | `20` or more | `2` | `5` or more | At least `200` | Separate approval | Stronger descriptive evidence. |
| Optional official reference tier | Selected cases | `official_upstream_reference` | Lower repeat count if cost is high | Separate approval | Separate cap | External context only, explicitly caveated. |

Tier 1 requires this exact future approval phrase before any live OpenAI call:

`I approve up to 100 OpenAI calls and a $5.00 estimated cap for Task 18B controlled domain ablation pilot`

The cost is estimate-only, not billing proof.

## Case Selection

Use cached/materialized recent `XOM`/`SPY` cases where deterministic labels are
known. Labels must report `missing=0`, and `UNKNOWN=0` is required for the
primary accuracy denominator. Cases must be selected before seeing model
outputs, and no case may be removed after output inspection. Avoid tightly
clustered decision dates where possible.

The original 2020 `XOM` target remains a separate reproduction/debug target. It
must not be mixed into the recent-panel controlled ablation.

## Labels And Metrics

Primary horizons are 63 and 126 trading days. Labels should use the
benchmark-adjusted Task 12/labeler policy. UNKNOWN labels are excluded from
accuracy denominators, and any UNKNOWN count must be reported.

Primary metric:

- Label-match accuracy by horizon.

Secondary metrics:

- All-run accuracy.
- Per-case majority-vote accuracy.
- Action stability and action entropy.
- Domain-on decision-change rate relative to domain-off.
- Changed-decision improvement count.
- Changed-decision worsening count.
- Changed-decision neutral count.
- Token usage.
- Estimated cost.

No investment-return claim should be made unless a separate return-focused
design is written and audited.

## Repeated-Run Policy

Each case-method pair is run `K` times, with seeds pre-declared before live
execution. All results are retained. Cache hits must be reported separately
from live calls. No cherry-picking is allowed.

Aggregation rules:

- Report all-run accuracy.
- Report majority action per case-method.
- If the majority action is tied, mark `majority_action=UNKNOWN`.
- Report the stability distribution.
- Report every failed run; do not silently drop failures.

Repeated runs should not be treated as independent cases without caveat.

## Statistical Plan

Analysis is descriptive first. Bootstrap confidence intervals may be reported if
sample size permits. Paired comparisons should be by case. McNemar or Wilcoxon
tests may be used only if assumptions and sample size are reasonable. Small-n
warnings are required.

Do not use statistical-significance wording unless preconditions and tests are
explicitly satisfied and audited.

## Leakage And Prompt-Safety Gates

Prompt contexts must exclude label windows, future returns, future prices, and
post-decision rows. Input snapshots must be hashed. Raw prompts are not printed.
Raw LLM outputs may be stored only in ignored artifacts. Generated outputs must
remain ignored, and `.env` must never be printed.

Before any live Task 18B run:

- Snapshot readiness must pass.
- Labels must have `missing=0` and `UNKNOWN=0` for the primary denominator.
- Prompt leakage preview must pass.
- Dry-run must report `openai_calls=0`.
- Cost and call caps must be configured.
- Explicit user approval must be provided.

## Interpretation Policy

If `domain_on_proposed` outperforms `domain_off_internal_baseline`, describe it
as controlled exploratory evidence, not proof. If results are mixed, report
mixed results. If repeated-run instability is high, emphasize instability.
Official upstream comparison remains caveated. This design provides no
investment advice, no financial advice, no procurement advice, and no legal
advice.

## Relationship To The Original Paper Or Presentation

The original paper/presentation reports proposed oil-domain method `BUY` and
existing TradingAgents model `SELL` for `XOM` on `2020-11-19`. The current
project has not completed an exact original-paper reproduction. Task 17C
produced a constrained upstream artifact normalized to `BUY`, which differs
from the reported existing-model `SELL`.

Task 18A designs a stronger future ablation protocol rather than retroactively
validating the original claim. Original 2020 `XOM` reproduction remains
separate from the recent-panel controlled ablation.
