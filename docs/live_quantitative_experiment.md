# Live Quantitative Experiment Roadmap

Task 11 adds the first live-data foundation for the research pipeline. Task 12
adds deterministic market outcome labels from local cached snapshots only. These
layers do not call OpenAI, run LLM decisions, or execute the live TradingAgents
graph.

## Task 11-14 Roadmap

- Task 11: build live case sets and collect or plan external data snapshots.
- Task 12: label forward outcomes from cached label-only data.
- Task 13A: define LLM output schemas, cache helpers, parsers, and cost estimates.
- Task 13B: build offline prompt contexts from controlled method variants and cached metadata.
- Task 13C-13D: add explicit OpenAI execution and run controlled LLM decision experiments.
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

## Task 13A: LLM Schema And Cache Foundation

Task 13A prepares future LLM experiments without running them. It defines LLM
output records, live decision records, live evaluation manifests, deterministic
cache keys, JSONL cache storage helpers, a deterministic decision parser, and
configuration-driven cost estimates.

The OpenAI runtime config is a safety estimate only. Task 13A does not call
OpenAI, build prompts, invoke external data providers, run TradingAgents, or
perform statistical testing. Future cached LLM outputs are ignored under
`results/llm_cache/`, and future live research outputs are ignored under
`results/live_research_eval/`.

## Task 13B: Offline Prompt Context Preview

Task 13B defines six controlled live-evaluation method variants in
`configs/live_experiments/live_method_matrix.yaml` and builds deterministic
prompt contexts from Task 11 cases plus local normalized snapshot metadata. It
does not call OpenAI, provider APIs, embeddings, TradingAgents, or external
services.

Prompt contexts use only information available on or before the case decision
date. Task 12 label fields, future returns, target dates, future prices,
post-decision rows, and `price_label_window` records are excluded from prompt
text and messages. Label files may be referenced only to document excluded
fields.

```bash
python scripts/preview_live_prompt_context.py \
  --cases data/cases/live_panel_2020_2024.csv \
  --case-id XOM_2020_03_31 \
  --method-matrix configs/live_experiments/live_method_matrix.yaml \
  --method-id full_reliability_workflow \
  --snapshot-dir data/live_snapshots/task11_plan \
  --labeled-cases data/cases/live_panel_2020_2024_labeled.csv \
  --seed 1 \
  --output-json results/live_research_eval/task13b_preview/full_prompt.json \
  --output-md results/live_research_eval/task13b_preview/full_prompt.md \
  --print-summary
```

The command prints hashes, warning counts, evidence counts, and output paths by
default. Full prompt printing is opt-in with `--show-prompt`. Generated previews
are ignored under `results/live_research_eval/`.

## Current Limitations

- Task 11 makes no performance claim.
- Task 12 labels are not a performance claim.
- Task 13B prompt previews are not model results or performance evidence.
- Task 11/12/13B outputs are not paper-ready and not statistically conclusive.
- Task 11/12/13B outputs do not provide financial/procurement/legal advice.
- Provider endpoint behavior may need provider-plan-specific adjustment.
- Task 13C-13D LLM execution and Task 14 statistical evaluation remain future work.
