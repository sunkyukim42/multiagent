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
| Selected commit | `TBD` |
| Selected tag | `TBD` |
| Selection status | `pending` |

No fake upstream commit or tag is selected in Task 17C.0. A future task should
prefer a stable release tag if one is selected later; otherwise it must pin an
exact commit hash. The future task must record clone date, upstream README
state, and upstream CHANGELOG or release-note state when those materials are
reviewed.

## License And Terms Review

License and terms review is required and remains pending. A future task must
record the upstream license file path or source, whether redistribution is
allowed, and whether vendor-copy use is allowed.

Task 17C.0 does not vendor upstream source into this repository. No upstream
source should be committed here without separate approval.

## Isolated Checkout Policy

The future upstream checkout must be outside this repository or under an
ignored results path. The recommended ignored path is:

`results/external_baselines/tradingagents_upstream/`

Do not commit upstream source into this repository. Do not modify dependency
files or lockfiles in Task 17C.0. A future task must use an isolated
environment for upstream setup.

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
| Task 17C.1 | External checkout and dry/mock preflight | Future |
| Task 17C.2 | Single-case official baseline live preflight | Future |
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
