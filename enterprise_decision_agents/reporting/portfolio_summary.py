from __future__ import annotations

from enterprise_decision_agents.reporting.benchmark_summary import _fmt
from enterprise_decision_agents.reporting.markdown_report import DISCLAIMER
from enterprise_decision_agents.reporting.report_schema import BenchmarkPackSummary


def render_portfolio_summary(summary: BenchmarkPackSummary, report_id: str) -> str:
    lines = [
        f"# Portfolio Summary: {report_id}",
        "",
        DISCLAIMER,
        "",
        "## Problem Statement",
        "",
        "Enterprise decision agents need domain context, auditable evidence, and reliability checks before outputs are trusted.",
        "",
        "## Technical Architecture",
        "",
        "The demo composes Domain Registry metadata, API-free experiments, offline RAG, Evidence Ledger records, Reliability Guardrails, and a deterministic LangGraph workflow.",
        "",
        "## Implemented Modules",
        "",
        "- Task 1: stabilization and API-free checks.",
        "- Task 2: YAML-backed Domain Registry.",
        "- Task 3: Experiment Runner with mock methods.",
        "- Task 4: offline local RAG index and retrieval.",
        "- Task 5: Evidence Ledger.",
        "- Task 6: deterministic Reliability Guardrails.",
        "- Task 7 and 7.1: optional reliability-aware workflow and runtime cleanup.",
        "",
        "## Demo Commands",
        "",
        "```bash",
        "python scripts/run_benchmark_pack.py --config configs/benchmarks/task8_full_demo.yaml --output-dir results/benchmark_packs/task8_full_demo --pack-id task8_full_demo --rebuild-index",
        "python scripts/generate_research_report.py --benchmark-dir results/benchmark_packs/task8_full_demo --output-dir results/reports/task8_research --report-id task8_research",
        "python scripts/generate_portfolio_summary.py --benchmark-dir results/benchmark_packs/task8_full_demo --output-dir results/reports/task8_portfolio --report-id task8_portfolio",
        "```",
        "",
        "## Reliability KPIs",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    for key, value in sorted(summary.aggregate_metrics.items()):
        lines.append(f"| {key} | {_fmt(value)} |")
    lines.extend(
        [
            "",
            "## Enterprise Value Proposition",
            "",
            "- Makes decision traces inspectable through ledger and reliability artifacts.",
            "- Keeps demos offline and reproducible without API keys.",
            "- Separates research packaging from live agent execution.",
            "",
            "## Engineering Practices",
            "",
            "- API-free tests and smoke checks.",
            "- Secret-safe output validation.",
            "- Generated artifacts ignored by git.",
            "- Reproducible command-line workflows.",
            "",
            "## Limitations",
            "",
            "- Sample benchmarks are illustrative only.",
            "- The reports are not investment or procurement advice.",
            "- No interactive web UI, PDF, PowerPoint, production auth, or live agent integration is included.",
        ]
    )
    return "\n".join(lines) + "\n"
