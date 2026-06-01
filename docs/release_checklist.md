# Release Checklist

Use this checklist before publishing or presenting the repository.

## Verification Commands

- Run `python -m compileall tradingagents enterprise_decision_agents tests scripts`.
- Run `pytest`.
- Run `python scripts/smoke_test.py`.
- Run `python scripts/validate_domains.py`.
- Run `python scripts/validate_domains.py --check-env`.
- Run the offline Task 8 benchmark pack.
- Generate the Task 8 research report.
- Generate the Task 8 portfolio summary.
- Run `git diff --check`.
- Run `git status --short --ignored`.

## Safety Checks

- Confirm `.env` is ignored and untracked.
- Confirm generated artifacts under `results/` and `data/indexes/` are ignored.
- Confirm no generated artifacts are staged.
- Run a redacted secret scan over changed source, configs, docs, tests, and generated reports.
- Confirm reports do not contain raw API keys or secret-like values.

## Presentation Checks

- Confirm reports state that sample outputs are synthetic and illustrative.
- Confirm reports do not claim paper-ready quality.
- Confirm reports do not provide financial, procurement, or legal advice.
- Confirm heuristic groundedness is described as lexical/heuristic, not semantic entailment.
- Confirm live `python main.py` remains separate from the offline demo.
