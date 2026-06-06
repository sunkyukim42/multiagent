# Ten-Case Recent API Live Pilot Results

## Scope

This document records the Task 16B live run and Task 16B.3 read-only audit as
a descriptive 10-case recent `XOM` API pilot. It used two controlled methods
and one seed. It is not the original 2020 `XOM` reproduction, not an official
TradingAgents baseline reproduction, not paper-ready, not statistically
conclusive, makes no performance claim, and provides no
financial/procurement/legal advice.

Generated artifacts remain ignored under `results/`, `results/llm_cache/`,
and `data/live_snapshots/`. This tracked note summarizes audited fields only;
it does not include full prompt text, full model-response text, API keys, or
generated live outputs.

## Method Boundary: Prompt Proxies, Not Official TradingAgents Graph Runs

`baseline_tradingagents_like` is an offline TradingAgents-like prompt proxy. It
does not execute the official TauricResearch/TradingAgents graph, CLI, or
upstream codebase, and it is not the official TradingAgents baseline result.

`domain_agent_only` is a controlled prompt/input variant that adds compact
domain context under the same local guarded runner. It is not a live modified
TradingAgents graph execution.

Both methods used the local guarded OpenAI runner with cached and materialized
snapshots. They should be interpreted as prompt-proxy variants only. An
official upstream TradingAgents baseline reproduction remains future work and
would require a pinned upstream repository version or commit, fixed model and
configuration, deterministic data snapshot policy, explicit call and cost caps,
and a separate audit.

## Data And Run Path

- Cached and materialized Alpha Vantage snapshots supplied the recent `XOM`
  and `SPY` data.
- Deterministic 63-day and 126-day outcome labels were generated from
  label-only future windows.
- Label windows and post-decision rows were excluded from prompt input.
- The guarded OpenAI live runner enforced explicit call and cost caps.
- Task 14 summary and KCI-style artifacts were generated offline from the
  completed live decisions.
- Generated outputs remain ignored and unstaged.

## Label Summary

| Field | Value |
| --- | ---: |
| Cases | `10` |
| Labels | `20` |
| Missing labels | `0` |
| UNKNOWN labels | `0` |
| BUY labels | `14` |
| HOLD labels | `6` |

## Live Run Summary

| Field | Value |
| --- | --- |
| Evaluation ID | `task16b_recent_10case_2method_openai` |
| Methods | `2` |
| Seeds | `1` |
| Planned / completed | `20 / 20` |
| OpenAI calls | `20` |
| Failed rows | `0` |
| Provider calls | `0` |
| Model | `gpt-4.1-mini` |
| Input tokens | `26,946` |
| Output tokens | `3,809` |
| Total tokens | `30,755` |
| Estimated cost | `$0.0168728` |
| Cost cap | `$1.00` |

The cost value is estimate-only and not billing proof.

## Method Summary

| Display label | Method ID | Runs | 3M accuracy | 126D accuracy |
| --- | --- | ---: | ---: | ---: |
| Baseline TradingAgents-like prompt proxy | `baseline_tradingagents_like` | `10` | `0.8` | `0.2` |
| Domain-context prompt variant | `domain_agent_only` | `10` | `0.8` | `0.2` |

The display labels are deliberately descriptive. They do not identify an
official upstream TradingAgents execution.

## Pairwise Summary

| Horizon | Comparison | Difference |
| --- | --- | ---: |
| `63d` | `domain_agent_only - baseline_tradingagents_like` | `0.0` |
| `126d` | `domain_agent_only - baseline_tradingagents_like` | `0.0` |

There was no observed aggregate difference between the two prompt variants in
this pilot. This is not an official TradingAgents-vs-domain comparison.

## Interpretation

Both prompt variants had the same aggregate 3M and 126D accuracy in this
10-case sample. The 3M match rate was higher than the 126D match rate in this
sample. The recent decision dates are clustered within one compact data window,
so independence is limited, and the sample remains small.

This result supports only a descriptive audit artifact. It does not support a
method superiority claim, a statistical conclusion, investment usefulness, or
financial/procurement/legal advice.

## Relationship To The Original Paper Or Presentation

The original paper or presentation describes adding an oil-domain analysis
pipeline to TradingAgents and comparing against an existing TradingAgents model
on `XOM` for `2020-11-19`. Task 16B does not reproduce that comparison.

Task 16B uses recent 2026 cached API data and controlled prompt variants. The
original 2020 `XOM` reproduction and official upstream TradingAgents baseline
reproduction remain future work.

## Future Official Baseline Design

`docs/official_tradingagents_baseline_reproduction_design.md` records the Task
17A plan for a future official TauricResearch/TradingAgents baseline
reproduction. That design is planning only. It does not clone or run upstream
code, does not call OpenAI or providers, and does not change the prompt-proxy
status of this Task 16B pilot.

## Future Controlled Ablation Design

`docs/controlled_domain_ablation_design.md` records the Task 18A plan for a
future internal domain-on/off ablation. That controlled path is the planned
route for stronger exploratory evidence because it holds the local runner,
cases, labels, snapshots, model, parser, and cost/call caps fixed while
changing only domain-specific oil context. Task 16B remains descriptive and is
not performance evidence.

## Safety

- Full prompt text is not included.
- Full model-response text is not included.
- API keys are not included.
- Generated outputs are not committed.
- Raw LLM outputs exist only in ignored live/cache audit artifacts.
- This document provides no advice.
- Not paper-ready.
- Not statistically conclusive.
- No performance claim.
- No financial/procurement/legal advice.
