# Live Quantitative Experiment Roadmap

Task 11 adds the first live-data foundation for the research pipeline. Task 12
adds deterministic market outcome labels from local cached snapshots only. These
layers do not call OpenAI, run LLM decisions, or execute the live TradingAgents
graph.

## Task 11-14 Roadmap

- Task 11: build live case sets and collect or plan external data snapshots.
- Task 12: label forward outcomes from cached label-only data.
- Task 13: run controlled LLM decision experiments.
- Task 14: run statistical evaluation and write paper-facing analysis.

## API Keys

Live provider calls require explicit `--allow-live-api` and the relevant local
environment variable:

- `FRED_API_KEY`
- `ALPHAVANTAGE_API_KEY`
- `FINNHUB_API_KEY`
- `THENEWSAPI_KEY`

The Task 11 default commands are plan-only, dry-run, or cache-only. They do not
read or print secret values.

## Cache-First Architecture

Snapshots are stored under ignored `data/live_snapshots/<experiment_id>/` paths.
Repeated experiments should read cached raw and normalized snapshots instead of
calling provider APIs again. Collection reports are written under ignored
`results/live_collection/<experiment_id>/` paths.

## Rate-Limit Safety

Provider limits live in `configs/live_experiments/provider_limits.yaml`. The
values are conservative safety defaults, not authoritative provider-plan claims.
The user must verify current provider terms before large experiments.

## Temporal Leakage Boundary

Agent-input snapshots use data up to the decision date. Any post-decision data
is label-only, marked as containing post-decision data, and not usable for agent
input. This separation is required before Task 12 outcome labeling.

## Task 12: Cache-Only Labels

Task 12 reads the Task 11 case panel and locally cached normalized price JSONL
files. It computes raw return, benchmark return, and excess return per horizon,
then writes BUY/HOLD/SELL/UNKNOWN labels and a label manifest. It never calls
provider APIs, OpenAI, LLMs, embeddings, TradingAgents, or external services.

The default policy is benchmark-adjusted against `SPY`, uses primary horizons of
63 and 126 days, and marks missing ticker or benchmark prices as `UNKNOWN`.
Future prices are label-only evaluation data and must not be used as agent
input. Raw-return fallback is disabled unless explicitly enabled by policy and
CLI override.

```bash
python scripts/label_market_outcomes.py \
  --cases data/cases/live_panel_2020_2024.csv \
  --snapshot-dir data/live_snapshots/task11_plan \
  --policy configs/live_experiments/labeling_policy.yaml \
  --output-csv data/cases/live_panel_2020_2024_labeled.csv \
  --output-jsonl data/cases/live_panel_2020_2024_labeled.jsonl \
  --manifest data/cases/live_panel_2020_2024_label_manifest.json \
  --report-dir results/live_labels/live_panel_2020_2024 \
  --label-run-id live_panel_2020_2024 \
  --max-cases 5 \
  --print-summary
```

Label reports are generated under ignored `results/live_labels/` paths. The
canonical labeled case files under `data/cases/` are trackable when generated.

## Current Limitations

- Task 11 makes no performance claim.
- Task 12 labels are not a performance claim.
- Task 11/12 outputs are not paper-ready and not statistically conclusive.
- Task 11/12 outputs do not provide financial/procurement/legal advice.
- Provider endpoint behavior may need provider-plan-specific adjustment.
- Task 13 LLM decisions and Task 14 statistical evaluation remain future work.
