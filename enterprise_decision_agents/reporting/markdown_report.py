from __future__ import annotations

from enterprise_decision_agents.reporting.benchmark_summary import _fmt
from enterprise_decision_agents.reporting.report_schema import BenchmarkPackSummary


DISCLAIMER = (
    "Sample outputs are synthetic and illustrative. They are not paper-ready benchmarks, "
    "not financial advice, and not procurement advice. Heuristic groundedness is not semantic entailment."
)


def render_research_report(summary: BenchmarkPackSummary, report_id: str) -> str:
    lines = [
        f"# Research Report: {report_id}",
        "",
        DISCLAIMER,
        "",
        "## Motivation",
        "",
        "This offline package demonstrates a reliability-aware domain-specific multi-agent RAG pipeline over synthetic sample cases.",
        "",
        "## Architecture Summary",
        "",
        "Domain Registry -> Experiment Runner -> Local RAG -> Evidence Ledger -> Reliability Guardrails -> Reliability Workflow -> Reporting.",
        "",
        "## Pipeline Stages",
        "",
        "- Sample cases and mock methods define reproducible inputs.",
        "- Local RAG retrieves metadata-filtered candidate evidence.",
        "- Evidence Ledger records claim-evidence links.",
        "- Guardrails compute deterministic reliability metrics.",
        "- Workflow routes to final report, retry, human review, or stop.",
        "",
        "## Sample Cases",
        "",
        "| Workflow | Domain | Case | Ticker | Decision Date | Task Type |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for run in summary.run_summaries:
        lines.append(
            f"| {run.workflow_run_id} | {run.domain or ''} | {run.case_id or ''} | {run.ticker or ''} | {run.decision_date or ''} | {run.task_type or ''} |"
        )
    lines.extend(
        [
            "",
            "## Metrics",
            "",
            "| Metric | Value |",
            "| --- | ---: |",
        ]
    )
    for key, value in sorted(summary.aggregate_metrics.items()):
        lines.append(f"| {key} | {_fmt(value)} |")
    lines.extend(["", "## Route And Status Summary", "", "| Type | Counts |", "| --- | --- |"])
    lines.append(f"| Routes | {_count_text(summary.route_counts)} |")
    lines.append(f"| Statuses | {_count_text(summary.status_counts)} |")
    lines.extend(
        [
            "",
            "## Limitations",
            "",
            "- The sample data is synthetic and illustrative.",
            "- The evaluation is not a statistically powered benchmark.",
            "- Groundedness is a deterministic lexical heuristic, not semantic entailment.",
            "- Live TradingAgents execution and external APIs are outside this package.",
            "",
            "## Next Research Steps",
            "",
            "- Add larger curated datasets with explicit labels.",
            "- Compare reliability-aware routing against live baselines under controlled API usage.",
            "- Add statistical tests only after dataset size and label quality are sufficient.",
        ]
    )
    return "\n".join(lines) + "\n"


def _count_text(counts: dict[str, int]) -> str:
    if not counts:
        return "none"
    return ", ".join(f"{key}={value}" for key, value in sorted(counts.items()))
