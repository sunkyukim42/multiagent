# Live Quantitative Experiment Roadmap

Task 11 adds the first live-data foundation for the research pipeline. Task 12
adds deterministic market outcome labels from local cached snapshots only. These
layers do not call OpenAI, run LLM decisions, or execute the live TradingAgents
graph.

## Task 11-15A Roadmap

- Task 11: build live case sets and collect or plan external data snapshots.
- Task 12: label forward outcomes from cached label-only data.
- Task 13A: define LLM output schemas, cache helpers, parsers, and cost estimates.
- Task 13B: build offline prompt contexts from controlled method variants and cached metadata.
- Task 13C: add gated OpenAI runner and deterministic fake runner.
- Task 13D: run controlled batch LLM decision experiments.
- Task 14: run offline descriptive statistical summaries and write KCI-style tables.
- Task 15A: prepare and inspect one real XOM/SPY snapshot micro-pilot.
- Task 15D/15E: package a capped five-case recent XOM live pilot as
  descriptive documentation only.

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

## Task 13C: Gated OpenAI Runner

Task 13C adds request/response schemas, a deterministic fake runner, live
OpenAI gating, call caps, cost caps, and conversion into Task 13A
`LLMDecisionOutput` records. It does not call external provider APIs, does not
run TradingAgents, and does not perform statistical testing.

Default runner behavior refuses live OpenAI calls. A future caller must pass an
explicit live flag before the runner reads `OPENAI_API_KEY` from the local
environment, and key values are never printed or stored. Tests use fake outputs
and guardrail responses only. Pricing remains an estimate from config and must
be verified before any real live run.

## Task 13D: Batch Live Research Evaluation Runner

Task 13D runs controlled `case x method x seed` decision batches using Task 13B
prompt construction, Task 13A cache/output schemas, and Task 13C fake or gated
OpenAI runners. Default config mode is cache-only, and safe validation can use
`--dry-run` or `--fake-runner` without reading API keys or making paid calls.

```bash
python scripts/run_live_research_evaluation.py \
  --config configs/live_experiments/live_research_eval_default.yaml \
  --cases data/cases/live_panel_2020_2024.csv \
  --labeled-cases data/cases/live_panel_2020_2024_labeled.csv \
  --snapshot-dir data/live_snapshots/task11_plan \
  --method-matrix configs/live_experiments/live_method_matrix.yaml \
  --openai-runtime configs/live_experiments/openai_runtime.yaml \
  --output-dir results/live_research_eval/task13d_fake \
  --cache-dir results/llm_cache/task13d_fake \
  --evaluation-id task13d_fake \
  --fake-runner \
  --fake-action BUY \
  --max-cases 2 \
  --max-methods 2 \
  --seeds 1 \
  --print-summary
```

Live OpenAI mode requires `--allow-live-openai` plus explicit case, method,
call, and cost caps. Task 12 labels, returns, target dates, future prices, and
label statuses are loaded only after prompt construction and never enter prompt
text or messages. Task 13D writes ignored outputs under
`results/live_research_eval/` and `results/llm_cache/`; it makes no performance
claim.

## Task 14: Offline Summary And Statistical Artifacts

Task 14 reads Task 13D decision outputs and Task 12 labels from local files. It
computes descriptive method metrics, paired method comparisons, bootstrap
confidence intervals, McNemar/Wilcoxon artifacts, case-level results, and
KCI-style Markdown/CSV tables. It never calls OpenAI, provider APIs,
embeddings, TradingAgents, `python main.py`, or external services.
The default config uses `primary_horizons` and a `statistical_tests` block while
retaining legacy key compatibility.

```bash
python scripts/summarize_live_experiment.py \
  --config configs/live_experiments/live_summary_default.yaml \
  --decisions results/live_research_eval/task14_fake_input/decisions.jsonl \
  --llm-outputs results/llm_cache/task14_fake_input/llm_outputs.jsonl \
  --labeled-cases data/cases/live_panel_2020_2024_labeled.csv \
  --output-dir results/live_experiment_summary/task14_fake_summary \
  --table-dir results/live_kci_tables/task14_fake_summary \
  --summary-id task14_fake_summary \
  --baseline-method-id baseline_tradingagents_like \
  --comparison-method-ids domain_agent_only \
  --horizons 63,126 \
  --bootstrap-iterations 200 \
  --bootstrap-seed 42 \
  --allow-fake-runner-outputs \
  --print-summary
```

Generated summaries are ignored under `results/live_experiment_summary/`,
statistical-test artifacts are ignored under `results/live_statistical_tests/`,
and live KCI tables are ignored under `results/live_kci_tables/`.

Fake-runner outputs are pipeline validation artifacts, not model performance
evidence. UNKNOWN labels are excluded from accuracy denominators and surfaced in
warning rates. Small samples are not paper-ready and not statistically
conclusive. Task 14 outputs make no performance claim and provide no
financial/procurement/legal advice.

## Task 15A: XOM/SPY Snapshot Micro-Pilot Preparation

Task 15A prepares one real historical micro-pilot case: `XOM` on `2020-11-19`,
benchmarked against `SPY` over 63-day and 126-day horizons. The pilot config is
`configs/live_experiments/pilot_xom_2020_11_19.yaml`. Default commands are
plan-only, dry-run, or local inspection; they do not call OpenAI, provider APIs,
embeddings, TradingAgents, or `python main.py`.
Alpha Vantage free-key price requests use `TIME_SERIES_DAILY` with compact
output. `TIME_SERIES_DAILY_ADJUSTED` may require premium access, and provider
`Information`, `Note`, or `Error Message` responses are not label-ready.

Build the one-case panel:

```bash
python scripts/build_live_case_set.py \
  --config configs/live_experiments/live_case_panel_2020_2024.yaml \
  --output-csv data/cases/pilot_xom_2020_11_19.csv \
  --output-jsonl data/cases/pilot_xom_2020_11_19.jsonl \
  --manifest data/cases/pilot_xom_2020_11_19_manifest.json \
  --tickers XOM \
  --dates 2020-11-19 \
  --print-summary
```

Plan target and benchmark snapshot requests without provider API calls:

```bash
python scripts/collect_live_snapshots.py \
  --cases data/cases/pilot_xom_2020_11_19.csv \
  --config configs/live_experiments/snapshot_collection_default.yaml \
  --provider-limits configs/live_experiments/provider_limits.yaml \
  --output-dir data/live_snapshots/pilot_xom_2020_11_19_plan \
  --collection-report-dir results/live_collection/pilot_xom_2020_11_19_plan \
  --experiment-id pilot_xom_2020_11_19_plan \
  --providers alphavantage,fred \
  --plan-only \
  --max-cases 1 \
  --max-calls 20 \
  --print-summary
```

Dry-run target and benchmark snapshot requests without provider API calls:

```bash
python scripts/collect_live_snapshots.py \
  --cases data/cases/pilot_xom_2020_11_19.csv \
  --config configs/live_experiments/snapshot_collection_default.yaml \
  --provider-limits configs/live_experiments/provider_limits.yaml \
  --output-dir data/live_snapshots/pilot_xom_2020_11_19_dry_run \
  --collection-report-dir results/live_collection/pilot_xom_2020_11_19_dry_run \
  --experiment-id pilot_xom_2020_11_19_dry_run \
  --providers alphavantage,fred \
  --dry-run \
  --max-cases 1 \
  --max-calls 20 \
  --print-summary
```

Inspect local readiness before labeling:

```bash
python scripts/inspect_live_snapshots.py \
  --snapshot-dir data/live_snapshots/pilot_xom_2020_11_19_dry_run \
  --cases data/cases/pilot_xom_2020_11_19.csv \
  --ticker XOM \
  --benchmark-ticker SPY \
  --decision-date 2020-11-19 \
  --horizons 63,126 \
  --providers alphavantage,fred \
  --output-json results/live_snapshot_quality/pilot_xom_2020_11_19_dry_run/quality.json \
  --output-md results/live_snapshot_quality/pilot_xom_2020_11_19_dry_run/quality.md \
  --print-summary
```

Optional live provider collection is manual and not part of default validation.
Free provider API limits may apply, so use cache/resume and conservative caps:

```bash
python scripts/collect_live_snapshots.py \
  --cases data/cases/pilot_xom_2020_11_19.csv \
  --config configs/live_experiments/snapshot_collection_default.yaml \
  --provider-limits configs/live_experiments/provider_limits.yaml \
  --output-dir data/live_snapshots/pilot_xom_2020_11_19 \
  --collection-report-dir results/live_collection/pilot_xom_2020_11_19 \
  --experiment-id pilot_xom_2020_11_19 \
  --providers alphavantage,fred \
  --allow-live-api \
  --max-cases 1 \
  --max-calls 20 \
  --resume \
  --print-summary
```

The optional live command does not call OpenAI and should be run only by the
user after verifying provider terms and local key setup. Snapshot quality
reports are ignored under `results/live_snapshot_quality/`. The micro-pilot is
not paper-ready, not statistically conclusive, makes no performance claim, and
provides no financial/procurement/legal advice.

### Audited Historical Price Fixture Fallback

When free live provider keys cannot return historical 2020 XOM/SPY prices, the
local fixture path can ingest manually supplied CSV files and a cited
`source_manifest.json`. This path performs no OpenAI calls and no live provider
API calls.
Real local fixture inputs belong under ignored `data/local_price_fixtures/`;
synthetic test fixtures under `tests/fixtures/price_fixture/` are not real
market data. The ingest CLI supports overrides for CSV paths, source manifest,
case metadata, horizons, cases file, output directory, and report directory.
The source manifest must include `fixture_id`, `created_by`, `created_at`,
`source_name`, `source_url_or_description`, `download_date`, `tickers`,
`date_range`, `license_or_terms_note`, and `notes`.
`--allow-missing-source-manifest` is a local debugging escape hatch only and
should not be used for publication or audit claims.

```bash
python scripts/ingest_price_fixture.py \
  --config configs/live_experiments/pilot_xom_2020_11_19_fixture.yaml \
  --print-summary
```

The command writes `price_fixture_ingestion_report.md` to the configured report
directory.

The fixture writes normalized local snapshots under
`data/live_snapshots/pilot_xom_2020_11_19_fixture` using provider
`local_price_fixture`. Inspect readiness before labeling:

```bash
python scripts/inspect_live_snapshots.py \
  --snapshot-dir data/live_snapshots/pilot_xom_2020_11_19_fixture \
  --cases data/cases/pilot_xom_2020_11_19.csv \
  --ticker XOM \
  --benchmark-ticker SPY \
  --decision-date 2020-11-19 \
  --horizons 63,126 \
  --providers local_price_fixture \
  --output-json results/live_snapshot_quality/pilot_xom_2020_11_19_fixture_quality/quality.json \
  --output-md results/live_snapshot_quality/pilot_xom_2020_11_19_fixture_quality/quality.md \
  --print-summary
```

Fixture-based labels use the fixture-specific policy:

```bash
python scripts/label_market_outcomes.py \
  --cases data/cases/pilot_xom_2020_11_19.csv \
  --snapshot-dir data/live_snapshots/pilot_xom_2020_11_19_fixture \
  --policy configs/live_experiments/labeling_policy_fixture.yaml \
  --output-csv results/live_labels/pilot_xom_2020_11_19_fixture/labeled.csv \
  --output-jsonl results/live_labels/pilot_xom_2020_11_19_fixture/labeled.jsonl \
  --manifest results/live_labels/pilot_xom_2020_11_19_fixture/label_manifest.json \
  --report-dir results/live_labels/pilot_xom_2020_11_19_fixture \
  --label-run-id pilot_xom_2020_11_19_fixture \
  --horizons 63,126 \
  --benchmark-ticker SPY \
  --print-summary
```

The CSV fixture and source manifest are manually supplied local inputs. Fixture
outputs are not performance evidence, not paper-ready, not statistically
conclusive, and not financial/procurement/legal advice. Post-decision fixture
rows are label-only and not usable for agent input.

## Task 15D/15E: Recent API Live Pilot Documentation

Task 15D.2 ran a capped five-case recent `XOM` pilot with two controlled
methods, one seed, ten approved OpenAI calls, and a `$0.50` estimated cost cap.
Task 15D.3 audited the result schemas, cache consistency, pairwise summaries,
cost record, prompt leakage boundaries, and safety disclaimers.

Task 15E records the audited result in
`docs/live_recent_pilot_results.md`. The document is descriptive only. It is not
paper-ready, not statistically conclusive, makes no performance claim, and
provides no financial/procurement/legal advice. Generated live outputs remain
ignored under `results/`, `results/llm_cache/`, and `data/live_snapshots/`.

## Current Limitations

- Task 11 makes no performance claim.
- Task 12 labels are not a performance claim.
- Task 13B prompt previews are not model results or performance evidence.
- Task 13C runner tests are not live OpenAI experiments.
- Task 13D batch outputs are not statistical evidence.
- Task 14 fake-runner summaries are validation artifacts only.
- Task 15A micro-pilot readiness is not performance evidence.
- Task 15D/15E recent pilot documentation is descriptive only.
- Task 11/12/13B/14 outputs are not paper-ready and not statistically conclusive.
- Task 11/12/13B/14 outputs do not provide financial/procurement/legal advice.
- Provider endpoint behavior may need provider-plan-specific adjustment.
- Real-data performance claims require cached live outputs, sufficient known labels, and independent audit.
