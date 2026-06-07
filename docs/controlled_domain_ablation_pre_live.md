# Controlled Domain Ablation Pre-Live Gate

## Scope

Task 18B is a pre-live and dry-run gate only. It does not call OpenAI, provider
APIs, upstream TauricResearch/TradingAgents, live TradingAgents,
`collect_live_snapshots.py`, or `python main.py`. It does not instantiate
`TradingAgentsGraph`, call `propagate`, or run upstream `analyze`.

This gate makes no performance claim, is not statistically conclusive, is not
paper-ready, and provides no financial/procurement/legal advice. It does not
complete an official TradingAgents baseline reproduction or the original 2020
`XOM` reproduction.

## Method Mapping

Task 18B defines exactly two local controlled prompt/input variants:

| Method | Role | Domain context | Other feature flags |
| --- | --- | --- | --- |
| `domain_off_internal_baseline` | Internal control | Disabled | RAG, ledger, guardrails, workflow, and live TradingAgents graph disabled. |
| `domain_on_proposed` | Proposed variant | Enabled | RAG, ledger, guardrails, workflow, and live TradingAgents graph disabled. |

The only intended controlled difference is `domain_specific_oil_context`. Both
methods use the same local runner, cases, labels, snapshots, parser, evidence
budget, seeds, cost cap, and call cap. Neither method executes official
TauricResearch/TradingAgents. Official upstream comparison remains an external
and caveated reference only.

The method matrix records machine-readable roles for audit checks:
`domain_off_internal_baseline` has role `internal_control`, and
`domain_on_proposed` has role `proposed_variant`. The same role value is also
stored under each method's metadata.

## Readiness Inputs

The source case set is `pilot_xom_recent_api_10case`:

- Cases: `results/live_collection/pilot_xom_recent_api_10case/cases.csv`
- Snapshots: `data/live_snapshots/pilot_xom_recent_api_10case`
- Labels: `results/live_labels/pilot_xom_recent_api_10case/labeled.csv`
- Quality reports: `results/live_snapshot_quality/pilot_xom_recent_api_10case`

Required readiness checks are `10` cases, `20` labels, horizons `63` and `126`,
`missing=0`, `UNKNOWN=0`, all label source snapshot paths present, no failed
snapshot records, and all snapshot quality results marked `ready_for_labeling`.

Prompt input may use only pre-decision `price_history` records marked usable for
agent input. `price_label_window` records are label-only, contain post-decision
data, and must remain excluded from prompt input.

## Prompt Leakage Gate

Summary-only prompt previews must run for the earliest, middle, and latest
cases, for both methods. The preview command must not use `--show-prompt`,
`--output-json`, or `--output-md`.

The summary may report only case ID, method ID, evidence count, warning count,
prompt hash, and input snapshot hash. The gate must confirm that label windows,
future prices, future returns, outcome labels, label statuses, and post-decision
rows are excluded from prompt input.

## Dry-Run Gate

The dry-run uses seeds `1,2,3,4,5`, `10` cases, and the two controlled methods.
Expected dry-run counts are:

- planned: `100`
- completed: `100`
- OpenAI calls: `0`
- failed: `0`
- skipped: `0`

The dry-run output and cache directories are ignored generated artifacts under
`results/live_research_eval/` and `results/llm_cache/`.

## Cost And Approval Gate

The planned future live pilot cap is `100` OpenAI calls and `$5.00` estimated
cost. Cost is estimate-only, not billing proof.

Live execution remains blocked until the user separately provides exactly:

`I approve up to 100 OpenAI calls and a $5.00 estimated cap for Task 18B controlled domain ablation pilot`

Task 18B itself does not use that approval phrase and does not perform live
OpenAI calls.

## Reporting Policy

The gate report may include readiness summaries, method flags, prompt-preview
hashes, dry-run counts, cost/call caps, scan counts, blockers, and the approval
phrase. It must not include API key values, `.env` contents, full prompts, raw
model responses, raw provider payloads, performance claims, statistical
significance claims, or advice.

No cherry-picking is allowed. All valid planned runs, dry-run records, warnings,
and failures must be reported.

## Task 18C Result

`docs/controlled_domain_ablation_live_results.md` records the completed Task
18C live pilot and Task 18D read-only audit. It keeps the result descriptive,
documents the segment-continuation provenance warning, records the all-`BUY`
63d label-base-rate caveat, and does not make a performance, statistical, or
advice claim.
