# Official TradingAgents Single-Case Run Plan

## Scope

Task 17C.2 is planning and pre-live gate documentation only. It does not run
upstream code, install upstream dependencies, call OpenAI, call provider APIs,
execute live TradingAgents, run `python main.py`, or run
`collect_live_snapshots.py`.

No official TauricResearch/TradingAgents baseline reproduction has been
completed. The original 2020 `XOM` reproduction remains future work. This plan
is not paper-ready, not statistically conclusive, makes no performance claim,
and provides no financial/procurement/legal advice.

## Upstream Pin

| Field | Value |
| --- | --- |
| Repository URL | `https://github.com/TauricResearch/TradingAgents.git` |
| Selected commit | `04f434e86db88e7707bf16db8ed7183f9764fe26` |
| Selected tag | `TBD` |
| Checkout path | `results/external_baselines/tradingagents_upstream` |
| License status | `reviewed_metadata_only`, not legal approval |

Task 17C.2 records command candidates from local metadata only. It does not
prove that any command works and does not execute or import upstream modules.

## Target

| Field | Value |
| --- | --- |
| Ticker | `XOM` |
| Decision date | `2020-11-19` |
| Purpose | Future official baseline single-case run |
| Status | `not_run` |

The target remains separate from Task 16 prompt-proxy pilots. Local
`baseline_tradingagents_like` and `domain_agent_only` outputs are not official
upstream TradingAgents outputs.

## Upstream Entrypoint Plan

Metadata inspection found package usage documented through
`TradingAgentsGraph` and `propagate`. The primary future path is a reviewed
wrapper in an isolated external environment that imports
`TradingAgentsGraph`, applies reviewed config values, and calls
`propagate("XOM", "2020-11-19", asset_type="stock")`. The wrapper must capture
the returned decision and relevant run metadata into ignored output files.

Secondary untested candidates are the installed `tradingagents` console command
and source invocation `python -m cli.main`. Metadata indicates the CLI uses an
interactive `analyze` command path, so the CLI must be reviewed before any live
use. No CLI command has been tested in Task 17C.2.

Observed metadata files and source names:

| Kind | Name |
| --- | --- |
| README | `README.md` |
| Package metadata | `pyproject.toml` |
| CLI source | `cli/main.py` |
| Default config source | `tradingagents/default_config.py` |

Environment variable names observed in metadata include `OPENAI_API_KEY`,
`ALPHA_VANTAGE_API_KEY`, `TRADINGAGENTS_LLM_PROVIDER`,
`TRADINGAGENTS_DEEP_THINK_LLM`, `TRADINGAGENTS_QUICK_THINK_LLM`,
`TRADINGAGENTS_LLM_BACKEND_URL`, `TRADINGAGENTS_OUTPUT_LANGUAGE`,
`TRADINGAGENTS_MAX_DEBATE_ROUNDS`, `TRADINGAGENTS_MAX_RISK_ROUNDS`,
`TRADINGAGENTS_CHECKPOINT_ENABLED`, `TRADINGAGENTS_BENCHMARK_TICKER`,
`TRADINGAGENTS_TEMPERATURE`, `TRADINGAGENTS_RESULTS_DIR`,
`TRADINGAGENTS_CACHE_DIR`, and `TRADINGAGENTS_MEMORY_LOG_PATH`. Only names are
recorded; no values are recorded.

## Environment And Data Policy

Future setup requires an isolated virtual environment outside this repository.
Task 17C.2 does not install dependencies and does not modify this repository's
dependency files or lockfiles. The future install command and future run
command must be reviewed before use.

Future runs must set output, cache, and memory paths under ignored `results/`
paths before upstream code is executed. Required environment variables must be
checked as present or missing without printing values.

Exact 2020 historical data freezing may be approximate. Upstream may fetch
current or live market, news, social, fundamental, or macro data even when an
analysis date is historical. A future run must document any live/current data
access and must prevent post-decision leakage where possible.

## Task 17C.3 Environment Import Preflight

Task 17C.3 created the ignored isolated environment at
`results/external_baselines/tradingagents_venv/` and installed the pinned
upstream checkout into that environment only. The environment is ignored by git
and must not be staged or committed.

Import probes used the ignored venv Python from a temporary directory outside
this repository with `PYTHON_DOTENV_DISABLED=1`. The probe imported
`tradingagents`, imported the `TradingAgentsGraph` symbol, and inspected the
`propagate` signature:

`(self, company_name, trade_date, asset_type: str = 'stock')`

The graph was not instantiated, `propagate` was not called, and no upstream
analysis command was run. Help-only probes for `tradingagents --help` and
`python -m cli.main --help` exited successfully and showed usage text without
entering analysis mode.

Task 17C.3 made no OpenAI call and no provider API call. It does not complete
the official TradingAgents baseline reproduction and does not complete the
original 2020 `XOM` reproduction.

## Task 17C Result Artifact

`docs/official_tradingagents_single_case_result.md` records the later
constrained upstream package execution artifact for `XOM` on `2020-11-19`.
That artifact normalized to `BUY` under `selected_analysts=[market]`, not the
full upstream default analyst set. It remains an execution trace and
integration checkpoint, not a completed original existing-model `SELL`
baseline reproduction and not the original 2020 `XOM` reproduction.

## Output Capture And Normalization

Raw future official output must be written only under:

`results/official_tradingagents_baseline/task17c_single_case/`

Full raw output must not be committed. Tracked docs should contain only safe
metadata, hashes, paths, and short summaries.

Normalization must use the Task 17B CLI:

`scripts/normalize_official_tradingagents_output.py`

Normalized output should be written under:

`results/official_baseline_normalization/task17c_single_case/`

Normalized records must store path/hash/summary metadata and must not store full
raw text.

## Gates And Caps

| Field | Value |
| --- | --- |
| Max OpenAI calls | `10` |
| Max estimated cost | `$1.00` |
| Cost status | Estimate only, not billing proof |

Required future approval phrase:

`I approve up to 10 OpenAI calls and a $1.00 estimated cap for Task 17C official TradingAgents baseline single-case run`

Go/no-go gates:

- Source tree clean.
- Upstream commit recorded.
- License metadata recorded.
- Isolated environment ready.
- Upstream install command reviewed.
- Required environment variables present in process without printing values.
- Future run command reviewed.
- Raw and normalized output directories ignored.
- Cost and call caps configured.
- Explicit approval phrase received.
- Normalization dry path tested with Task 17B fake fixtures.
- No generated outputs staged.

## Risks

- Upstream command may fail.
- Upstream data may be current or live rather than historical.
- Exact 2020 reproduction may be approximate.
- Dependency conflicts may require external isolation.
- Model outputs may be nondeterministic.
- Provider cost and rate limits may differ from estimates.
- This plan provides no advice.
