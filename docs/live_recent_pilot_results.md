# Recent API Live Pilot Results

## Scope

This document records the Task 15D.2 and Task 15D.3 five-case recent `XOM`
API pilot as a descriptive audit artifact. It is not the original 2020 `XOM`
reproduction path, not a paper-ready experiment, not statistically conclusive,
and not financial/procurement/legal advice.

The pilot used five recent decision dates:

| Case ID | Decision date |
| --- | --- |
| `XOM_2026_01_09` | `2026-01-09` |
| `XOM_2026_01_14` | `2026-01-14` |
| `XOM_2026_01_20` | `2026-01-20` |
| `XOM_2026_01_23` | `2026-01-23` |
| `XOM_2026_01_28` | `2026-01-28` |

All generated outputs remain under ignored `results/`, `results/llm_cache/`,
and `data/live_snapshots/` paths. The tracked source tree was clean during the
Task 15D.3 audit.

## Data Pipeline

The input pipeline used cached Alpha Vantage price history snapshots. Task
15D.1a materialized case-specific normalized snapshots from shared raw compact
payloads and retained raw provenance for auditability.

Labels were deterministic market-outcome labels over 63-day and 126-day
horizons. Label-window rows were marked as evaluation-only data and excluded
from prompt input. Prompt construction used only pre-decision snapshot context;
future return fields, label values, and post-decision rows were excluded.

## Run Configuration

| Field | Value |
| --- | --- |
| Evaluation ID | `task15d_recent_5case_2method_openai` |
| Cases | `5` |
| Methods | `baseline_tradingagents_like`, `domain_agent_only` |
| Seeds | `1` |
| OpenAI call cap | `10` |
| Estimated cost cap | `$0.50` |
| Actual OpenAI calls | `10` |
| Failed runs | `0` |

The live run made the capped OpenAI calls only after explicit approval. It did
not run provider collection, live TradingAgents, or `python main.py`.

## Label Summary

| Metric | Value |
| --- | --- |
| Labels | `10` |
| Missing labels | `0` |
| UNKNOWN labels | `0` |
| BUY labels | `7` |
| HOLD labels | `3` |

| Case ID | 63-day label | 126-day label |
| --- | --- | --- |
| `XOM_2026_01_09` | `BUY` | `BUY` |
| `XOM_2026_01_14` | `BUY` | `BUY` |
| `XOM_2026_01_20` | `BUY` | `HOLD` |
| `XOM_2026_01_23` | `BUY` | `HOLD` |
| `XOM_2026_01_28` | `BUY` | `HOLD` |

## Method Summary

The following metrics are descriptive counts from this tiny pilot only.

| Method | Runs | 3M accuracy | 6M accuracy | OpenAI calls | Estimated cost |
| --- | ---: | ---: | ---: | ---: | ---: |
| `baseline_tradingagents_like` | `5` | `0.6` | `0.4` | `5` | `$0.0039908` |
| `domain_agent_only` | `5` | `0.8` | `0.2` | `5` | `$0.0042088` |

| Horizon | Pairwise comparison | Difference |
| --- | --- | ---: |
| `63d` | `domain_agent_only - baseline_tradingagents_like` | `+0.2` |
| `126d` | `domain_agent_only - baseline_tradingagents_like` | `-0.2` |

## Cost And Token Summary

| Metric | Value |
| --- | ---: |
| Input tokens | `13,007` |
| Output tokens | `1,873` |
| Total tokens | `14,880` |
| Estimated cost | `$0.0081996` |
| Estimated cost cap | `$0.50` |

The cost value is computed from the local runtime pricing configuration and is
an estimate only, not billing proof.

## Interpretation

The results are descriptive only. `domain_agent_only` appears higher at the
63-day horizon in this five-case pilot, while `baseline_tradingagents_like`
appears higher at the 126-day horizon. The sample is too small to support a
superiority, reliability, or deployment claim.

The Task 14 summary includes small-sample warnings. The KCI-style tables state
that the outputs are not paper-ready, not statistically conclusive, make no
performance claim, and provide no financial/procurement/legal advice.

## Safety Boundaries

- This is a capped pilot artifact, not a production system.
- It makes no performance claim and no statistical conclusion.
- It provides no financial/procurement/legal advice.
- Generated outputs remain ignored and should not be staged as source files.
- Full prompts and full model responses are omitted from this tracked document.
- Future larger pilots need preregistered scope, explicit cost gates, cached
  provider inputs, independent audit, and the same leakage controls.
