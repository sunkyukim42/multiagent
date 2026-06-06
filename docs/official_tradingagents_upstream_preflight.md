# Official TradingAgents Upstream Preflight

## Scope

Task 17C.0 is planning and preflight only. It does not clone upstream code, run
upstream code, install upstream dependencies, call OpenAI, call provider APIs,
run live TradingAgents, run `python main.py`, or run
`collect_live_snapshots.py`.

No official TauricResearch/TradingAgents baseline reproduction has been
completed. The original 2020 `XOM` reproduction remains future work. This
preflight is not paper-ready, not statistically conclusive, makes no
performance claim, and provides no financial/procurement/legal advice.

## Upstream Source

| Field | Value |
| --- | --- |
| Repository URL | `https://github.com/TauricResearch/TradingAgents.git` |
| Selected commit | `04f434e86db88e7707bf16db8ed7183f9764fe26` |
| Selected tag | `TBD` |
| Selection status | `selected_commit_recorded` |

Task 17C.1 records the actual checked-out upstream commit. No fake upstream
commit or tag is selected. `selected_tag` remains `TBD`; a future task may
prefer a stable release tag if one is selected later, otherwise it must pin an
exact commit hash. Task 17C.1 records the current exact commit hash as the
selected reference.

## License And Terms Review

License and terms review is required. Task 17C.1 reviewed metadata only and
detected `LICENSE` with an obvious Apache License heading. This is not legal
approval. A future task must still decide whether redistribution is allowed and
whether vendor-copy use is allowed.

Task 17C.0 does not vendor upstream source into this repository. No upstream
source should be committed here without separate approval.

## Isolated Checkout Policy

The future upstream checkout must be outside this repository or under an
ignored results path. The recommended ignored path is:

`results/external_baselines/tradingagents_upstream/`

Do not commit upstream source into this repository. Do not modify dependency
files or lockfiles in Task 17C.0. A future task must use an isolated
environment for upstream setup.

## Task 17C.1 Metadata Checkout

Task 17C.1 cloned the public upstream repository into the ignored checkout path
for metadata inspection only. No upstream code was run, no upstream CLI was
run, no upstream Python module was imported, no upstream dependency was
installed, and no OpenAI or provider API call was made.

| Field | Value |
| --- | --- |
| Checkout path | `results/external_baselines/tradingagents_upstream` |
| Checkout ignored | `true` |
| Checkout date | `2026-06-06` |
| Branch | `main` |
| Commit | `04f434e86db88e7707bf16db8ed7183f9764fe26` |
| Tag selection | `TBD` |
| Tags detected | `8` tags, from `v0.1.0` through `v0.2.5` |
| License file detected | `LICENSE` |
| License metadata status | `reviewed_metadata_only`, not legal approval |
| README file detected | `README.md` |
| Dependency files detected | `pyproject.toml`, `requirements.txt`, `uv.lock` |
| Upstream run status | `not_run` |
| Upstream install status | `not_installed` |
| Official reproduction status | `not_completed` |

README metadata indicates installation and usage material is present. README
metadata also mentions API-key variable names such as `OPENAI_API_KEY`,
`ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, and `ALPHA_VANTAGE_API_KEY`; no values
were inspected or recorded. README metadata appears to reference live data and
model-temperature or nondeterminism concerns, which remain future audit items.

## Task 17C.2 Single-Case Run Plan

Task 17C.2 adds a tracked pre-live command plan for a future official upstream
single-case run on `XOM` for `2020-11-19`. It records `TradingAgentsGraph` /
`propagate` as the primary package-usage candidate and records the installed
`tradingagents` command plus `python -m cli.main` as secondary untested CLI
candidates. It does not run upstream code, install dependencies, call OpenAI,
call providers, or complete the official or original 2020 reproduction.

The detailed plan is in
`docs/official_tradingagents_single_case_run_plan.md`.

## Environment Plan

Future upstream setup requires a separate virtual environment. Task 17C.0 does
not create that environment and does not run an install command.

A future preflight must record:

- Python version.
- Upstream dependency installation command.
- Upstream provider and API-key requirements.
- Any dependency conflicts with this repository.
- Whether dependency resolution happened outside this repository.

## Model And Config Pinning Plan

A future official baseline run must pin:

- `llm_provider`.
- model names.
- temperature.
- debate rounds and research depth, if used by upstream.
- analysis date and ticker.
- upstream config values required for repeatability.
- whether upstream prompts and defaults are used unchanged.

## Data Policy

The original target is `XOM` on `2020-11-19`. Historical data freezing is
required where possible. If upstream uses live or current news, social, market,
fundamental, or macro sources, exact 2020 reproduction may be approximate.

The future run must prevent post-decision leakage. Local prompt-proxy results
from Task 16B must not be mixed with official upstream baseline outputs without
explicit caveats.

## Output Normalization

Future official upstream output should be normalized through the Task 17B
normalizer. Raw upstream output should be stored only under ignored `results/`
paths. Normalized records should store `raw_output_path` and `raw_output_hash`;
tracked docs should not include full raw output text.

## Future Live Gates

| Future task | Purpose | Status |
| --- | --- | --- |
| Task 17C.1 | External checkout and dry/mock preflight | Completed metadata-only checkout |
| Task 17C.2 | Single-case official baseline pre-live command plan | Planned as documentation/config/test gate |
| Task 17C | Approved official baseline single-case live run | Future |

The future Task 17C run remains blocked until upstream commit/tag selection,
license review, isolated checkout, environment plan, model/config pinning,
deterministic data policy, output normalization readiness, and explicit user
approval are complete.

Required future approval phrase:

`I approve up to 10 OpenAI calls and a $1.00 estimated cap for Task 17C official TradingAgents baseline single-case run`

## Risks

- Upstream repository behavior can change over time.
- Exact historical data may be unavailable.
- Provider or API behavior can change.
- Upstream dependencies may conflict with this repository.
- Model outputs may be nondeterministic.
- Cost estimates may differ from billing.
- This preflight provides no investment usefulness claim or advice.
