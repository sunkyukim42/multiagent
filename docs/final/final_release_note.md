# Final Release Note

## Release Status

The accepted final package is `task18f_final_package_refresh_rerun` at
`results/final_packages/task18f_final_package_refresh_rerun`. The generated
package is ignored output. The tracked source tree was clean during the release
audit, the protected-path diff was empty, validation passed, and the safety scan
passed with zero findings for secrets, raw prompt/response content, embedded raw
model output, affirmative overclaims, false reproduction claims, and
cherry-picking-risk wording.

The final package contains these copied artifacts:

- `one_page_research_statement`
- `graduate_lab_contact_summary`
- `portfolio_project_summary`
- `interview_story_bank`
- `kci_extension_roadmap`
- `final_demo_checklist`
- `project_limitations`
- `live_pilot_addendum`

## Research Narrative

This project extends TradingAgents-style multi-agent analysis with
domain-specific reliability and controlled-ablation tooling. The original
motivation is that generic TradingAgents-style workflows may not fully
incorporate industry-specific domain signals. This repository adds offline
reliability infrastructure, live-pilot scaffolding, official-upstream boundary
checks, and a controlled internal domain-on/off ablation. The wording here is
descriptive and cautious.

## Controlled Ablation Summary

Task 18C and Task 18D recorded a controlled internal ablation pilot with `10`
cases, `2` methods, `5` seeds, and `100` decision rows. The
`domain_off_internal_baseline` method is the `internal_control`; the
`domain_on_proposed` method is the `proposed_variant`; and the controlled
difference is `domain_specific_oil_context`.

In this controlled pilot, `domain_on_proposed` had higher 63d label-match, while
126d label-match was unchanged. The 63d labels were all `BUY`, so the 63d lift
may partly reflect stronger `BUY` propensity or action-bias alignment rather
than general superiority. The segment-continuation provenance caveat remains:
the first full `--fail-fast` attempt left `6` successful rows in cache but no
segment manifest, and two later segment manifests document `94` live OpenAI
calls as `4 + 90`. The final artifact has `100` unique successful decision rows.

This result is descriptive only, not statistically conclusive, no performance
claim, and no financial/procurement/legal advice.

## Official Upstream Boundary

Task 17C produced a constrained upstream package execution artifact for `XOM` on
`2020-11-19` at upstream commit
`04f434e86db88e7707bf16db8ed7183f9764fe26`. It used
`selected_analysts=[market]` and normalized to `BUY`.

That artifact is not full upstream default baseline, not original existing-model
`SELL` reproduction, and not original 2020 `XOM` reproduction. Historical
2020-only data freeze was not proven, and the current/live yfinance cache
warning remains part of the caveat.

## What Is Not Claimed

- No statistical-significance claim.
- No performance improvement claim.
- No investment usefulness claim.
- No financial/procurement/legal advice.
- No official TradingAgents reproduction.
- No original 2020 `XOM` reproduction.
- No production deployment claim.
- No cherry-picked result claim.
- Repeated seeds are not independent cases without caveat.

## Inspect Or Regenerate Safely

These commands are the safe offline inspection and regeneration path:

```powershell
python -m compileall tradingagents enterprise_decision_agents tests scripts
pytest
python scripts/smoke_test.py
python scripts/validate_domains.py
python scripts/validate_domains.py --check-env
python scripts/generate_final_package.py `
  --config configs/presentation/final_portfolio_package.yaml `
  --output-dir results/final_packages/task18f_final_package_refresh_rerun `
  --package-id task18f_final_package_refresh_rerun
```

The package generation command does not call OpenAI or providers. Generated
outputs remain ignored. Do not print `.env`. Live experiments require separate
explicit approvals and are not part of release-note regeneration.

## Artifact Hygiene And Safety

`.env` is ignored and was not printed. Generated results are ignored. Raw
prompts were not printed. Raw model responses were not printed. Raw model
outputs are retained only in ignored artifacts. The final package contains no
API keys, and no generated outputs are staged.

## Reviewer Reading Order

1. `README.md`
2. `docs/final/portfolio_project_summary.md`
3. `docs/final/live_pilot_addendum.md`
4. `docs/controlled_domain_ablation_live_results.md`
5. `docs/official_tradingagents_single_case_result.md`
6. `docs/final/project_limitations.md`
7. `results/final_packages/task18f_final_package_refresh_rerun/README_FINAL_PACKAGE.md`
   if generated locally

## Remaining Risks

- Task 18C has a segment-continuation provenance caveat.
- The 63d horizon has an all-`BUY` label-base-rate caveat.
- The 126d horizon was unchanged.
- The cases are a small sample with clustered recent dates.
- Repeated seeds are not independent cases without caveat.
- Cost estimates are not billing proof.
- Official upstream comparison remains caveated.
