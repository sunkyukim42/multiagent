# Official TradingAgents Baseline Reproduction Design

## Scope

Task 17A is design only. It does not call OpenAI, provider APIs, embeddings,
live TradingAgents, `python main.py`, or `collect_live_snapshots.py`. It does
not clone, install, or run the TauricResearch/TradingAgents repository. It is
not a completed official TradingAgents baseline reproduction, not the original
2020 `XOM` reproduction, not paper-ready, not statistically conclusive, makes
no performance claim, and provides no financial/procurement/legal advice.

## Motivation

Task 16B produced a recent 10-case prompt-proxy pilot. That pilot used
`baseline_tradingagents_like` and `domain_agent_only` as controlled local
prompt/input variants. It did not execute official TauricResearch/TradingAgents
graph code, CLI code, or upstream repository code.

The original paper or presentation compares a proposed oil-domain extension
against an existing TradingAgents baseline on `XOM` around `2020-11-19`. A
future official upstream baseline reproduction is needed to address that
methodological gap. Task 17A only designs the required controls and gates.

## Baseline Boundary

`baseline_tradingagents_like` is an offline prompt proxy. It must not be
treated as official upstream TradingAgents output. `domain_agent_only` is a
controlled prompt/input variant, not a live modified TradingAgents graph run.

An official baseline reproduction must use a pinned upstream repository version
or commit, an isolated environment, fixed model and configuration settings, and
a deterministic data policy. Official TradingAgents baseline reproduction
remains future work.

## Reproduction Targets

| Tier | Target | Purpose | Status |
| --- | --- | --- | --- |
| Tier A | `XOM` on `2020-11-19` | Reproduce official upstream TradingAgents baseline decision under pinned config | Future |
| Tier B | Task 16B recent 10-case `XOM` set | Later comparison against local prompt-proxy and domain-context variants | Future |

Tier A is the original 2020 `XOM` reproduction target. This document makes no
claim that the target has already been reproduced. Tier B remains separate from
the original 2020 target and requires separate approval before any live run.

## Upstream Pinning Plan

- Upstream URL: `https://github.com/TauricResearch/TradingAgents.git`.
- Upstream commit: `TBD`.
- Upstream tag: optional, `TBD`.
- Record clone date when a future task performs an external checkout.
- Record repository license and terms review before running upstream code.
- Do not vendor upstream code into this repository without separate approval.
- Prefer an isolated external checkout path that is ignored by git.

## Environment Plan

The future reproduction should use an isolated upstream environment. Task 17A
does not change this repository's dependency files or lockfiles. A future task
must document Python version, package installation strategy, provider
requirements, and API-key requirements before any upstream execution.

If upstream dependencies conflict with this repository, resolve them outside
this repository first. Any dependency or lockfile change here must be a
separate reviewed task.

## Model And Config Plan

A future official baseline run must pin:

- pin model name
- pin temperature
- pin max tokens, if applicable
- pin analyst depth, debate rounds, and other upstream run-depth options
- all upstream configuration values needed for repeatability
- whether upstream default prompts are used unchanged
- any adapter layer between upstream output and local audit schemas

The run manifest should record every pinned value and the upstream commit hash.

## Data Policy

The reproduction must avoid post-decision leakage. It should use deterministic
snapshots where possible and must distinguish upstream live data access from
local cached Alpha Vantage snapshots.

For the original 2020 `XOM` target, the future plan must define how historical
news, fundamental, market, and macro data are frozen. If exact historical
upstream data is unavailable, the run must be labeled approximate rather than a
full reproduction.

## Output Normalization Plan

The future run should capture the official upstream final decision and normalize
it to `BUY`, `HOLD`, `SELL`, or `UNKNOWN`. Raw upstream output should be stored
only in ignored artifacts. Full prompt text and full model-response text should
not be printed.

Each run should write a manifest with model, config, upstream commit, output
hashes, cost estimate, call count, and normalization status.

## Task 17B Fake-Output Normalization Preflight

Task 17B adds a local fake-fixture schema, parser, normalizer, and CLI for
testing how future official TauricResearch/TradingAgents output could be
accepted into local audit artifacts. It uses clearly synthetic fixture files
only and stores normalized records with raw output path and hash metadata, not
full raw output text.

Task 17B does not clone, install, or run upstream code. It does not call
OpenAI, provider APIs, live TradingAgents, `python main.py`, or
`collect_live_snapshots.py`. It is not a completed official TradingAgents
baseline reproduction, not the original 2020 `XOM` reproduction, makes no
performance claim, and provides no financial/procurement/legal advice.

## Task 17C.0 Upstream Preflight

Task 17C.0 records upstream selection, license review, isolated checkout, and
future live-run gates for a later official TauricResearch/TradingAgents
baseline reproduction. It keeps upstream commit and tag selection pending and
does not invent a fake upstream revision.

Task 17C.0 does not clone, install, or run upstream code. It does not call
OpenAI, provider APIs, live TradingAgents, `python main.py`, or
`collect_live_snapshots.py`. Official upstream reproduction remains future
work, and the original 2020 `XOM` reproduction remains future work.

Task 17C.1 records a metadata-only external checkout under the ignored
`results/external_baselines/tradingagents_upstream` path. It records upstream
commit `04f434e86db88e7707bf16db8ed7183f9764fe26` and license metadata status
`reviewed_metadata_only`; it does not run upstream code, install dependencies,
call live APIs, or complete the official baseline reproduction.

Task 17C.2 records a pre-live single-case command plan for future `XOM` on
`2020-11-19` execution. It identifies `TradingAgentsGraph.propagate` as the
primary package-usage candidate, keeps CLI candidates untested, routes raw
future output to ignored `results/` paths, and routes normalized output through
the Task 17B normalizer. It remains planning only and does not install
dependencies, run upstream code, call OpenAI, call providers, or complete the
official or original 2020 reproduction.

Task 17C.3 creates an ignored isolated environment and verifies import/help-only
readiness. It does not instantiate the graph, call `propagate`, run upstream
analysis, call OpenAI, call providers, or complete the official or original
2020 reproduction.

## Cost And Call Safety

Task 17B preflight should use dry-run, fixture, or mock output where possible.
No live OpenAI call is allowed before explicit user approval.

The first future live target should be the original 2020 `XOM` official
baseline single-case run with:

- max OpenAI calls: `10`
- max estimated cost: `$1.00`

Larger official baseline runs require separate approval.

Required future approval phrase:

`I approve up to 10 OpenAI calls and a $1.00 estimated cap for Task 17C official TradingAgents baseline single-case run`

## Comparison Policy

Do not compare official upstream baseline output against prompt-proxy results
without documenting methodological differences. Do not use a single case for a
method superiority claim. Use the Task 14 summary path only after comparable
outputs and labels exist.

The original 2020 reproduction target must remain separate from the recent
2026 prompt-proxy pilot.

## Go/No-Go Gates For Future Task 17B

- Upstream commit selected.
- License and terms reviewed.
- Isolated environment plan documented.
- Deterministic data policy documented.
- Source tree clean.
- Cost and call cap configured.
- Output normalization tested with fake upstream output.
- No live calls before explicit approval.
- No generated outputs staged.

## Risks

- Upstream repository behavior can change over time.
- Upstream data sources may be live/current rather than historical.
- Exact 2020 reproduction may be impossible without archived data.
- Dependency conflicts may require isolated setup.
- API costs can differ from estimates.
- Model outputs may vary across calls.
- Raw prompts or model outputs may contain sensitive context.
- This design provides no investment usefulness claim or advice.
