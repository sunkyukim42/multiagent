# Live Quantitative Experiment Roadmap

Task 11 adds the first live-data foundation for the research pipeline. It builds
a historical case panel and local snapshot cache, but it does not generate
labels, call OpenAI, run LLM decisions, or execute the live TradingAgents graph.

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

## Current Limitations

- Task 11 makes no performance claim.
- Task 11 is not paper-ready and not statistically conclusive.
- Task 11 does not provide financial/procurement/legal advice.
- Provider endpoint behavior may need provider-plan-specific adjustment.
