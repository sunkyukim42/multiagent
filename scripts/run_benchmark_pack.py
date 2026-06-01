from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from enterprise_decision_agents.evaluation.experiment_runner import ExperimentRunner, load_method_configs
from enterprise_decision_agents.orchestration.langgraph_workflow import run_reliability_workflow
from enterprise_decision_agents.reporting.ablation_summary import build_ablation_summaries
from enterprise_decision_agents.reporting.artifact_collector import collect_workflow_artifacts
from enterprise_decision_agents.reporting.benchmark_summary import build_pack_summary, save_benchmark_outputs
from enterprise_decision_agents.reporting.report_schema import BenchmarkRunSummary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run an offline Task 8 benchmark pack.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--pack-id", default=None)
    parser.add_argument("--rebuild-index", action="store_true")
    parser.add_argument("--max-runs", type=int, default=None)
    parser.add_argument("--fail-fast", action="store_true")
    parser.add_argument("--skip-existing", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = _load_config(args.config)
        output_dir = Path(args.output_dir)
        pack_id = args.pack_id or str(config.get("benchmark_id") or output_dir.name)
        summary, manifest, ablations = run_pack(
            config=config,
            config_path=args.config,
            output_dir=output_dir,
            pack_id=pack_id,
            rebuild_index=args.rebuild_index,
            max_runs=args.max_runs,
            fail_fast=args.fail_fast,
            skip_existing=args.skip_existing,
        )
        save_benchmark_outputs(output_dir, summary, manifest, ablations)
    except Exception as exc:
        print(f"Benchmark pack failed: {exc}", file=sys.stderr)
        return 1

    print(f"BenchmarkPack: {output_dir}")
    print(
        "Summary: "
        f"benchmark_id={summary.benchmark_id} "
        f"runs={len(summary.run_summaries)} "
        f"routes={_count_text(summary.route_counts)} "
        f"statuses={_count_text(summary.status_counts)} "
        f"warnings={len(summary.warnings)}"
    )
    return 0


def run_pack(
    *,
    config: dict[str, Any],
    config_path: str | Path,
    output_dir: Path,
    pack_id: str,
    rebuild_index: bool = False,
    max_runs: int | None = None,
    fail_fast: bool = False,
    skip_existing: bool = False,
) -> tuple[Any, dict[str, Any], list[Any]]:
    benchmark_id = str(config.get("benchmark_id") or pack_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    warnings: list[str] = []
    manifest: dict[str, Any] = {
        "benchmark_id": benchmark_id,
        "pack_id": pack_id,
        "config_path": str(config_path),
        "workflows": [],
        "experiments": [],
        "warnings": warnings,
    }

    _run_experiments(config.get("experiments", []), output_dir, manifest, warnings, fail_fast)

    run_summaries: list[BenchmarkRunSummary] = []
    workflows = list(config.get("workflows") or [])
    if max_runs is not None:
        workflows = workflows[:max_runs]
    expected_artifacts = [str(item) for item in config.get("expected_artifacts", [])]
    for workflow in workflows:
        workflow_dir = Path(workflow["output_dir"])
        try:
            if not (skip_existing and (workflow_dir / "workflow_state.json").exists()):
                state = _workflow_state_from_config(workflow, rebuild_index)
                run_reliability_workflow(state, workflow.get("workflow_config"))
            summary, run_manifest = collect_workflow_artifacts(
                workflow_dir,
                benchmark_id=benchmark_id,
                pack_id=pack_id,
                expected_artifacts=[str(item) for item in workflow.get("expected_artifacts", expected_artifacts)],
            )
            run_summaries.append(summary)
            manifest["workflows"].append(run_manifest)
            warnings.extend(summary.metadata.get("warnings", []))
        except Exception as exc:
            if fail_fast:
                raise
            message = f"{workflow.get('workflow_run_id', workflow_dir.name)} failed: {exc}"
            warnings.append(message)
            run_summaries.append(_failed_summary(benchmark_id, pack_id, workflow, message))
            manifest["workflows"].append({"workflow_dir": str(workflow_dir), "warnings": [message]})

    summary = build_pack_summary(
        benchmark_id=benchmark_id,
        run_summaries=run_summaries,
        warnings=warnings,
        metadata={
            "pack_id": pack_id,
            "display_name": config.get("display_name"),
            "description": config.get("description"),
            "domain": config.get("domain"),
            "cases": config.get("cases", []),
            "synthetic": True,
            "illustrative_only": True,
        },
    )
    ablations = build_ablation_summaries(run_summaries, config.get("method_components", []))
    return summary, manifest, ablations


def _load_config(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: benchmark config must be a mapping")
    if not data.get("benchmark_id"):
        raise ValueError(f"{path}: benchmark_id is required")
    return data


def _run_experiments(
    experiments: list[dict[str, Any]],
    output_dir: Path,
    manifest: dict[str, Any],
    warnings: list[str],
    fail_fast: bool,
) -> None:
    experiment_dir = output_dir / "experiments"
    for experiment in experiments:
        try:
            experiment_id = str(experiment.get("experiment_id") or "task8_experiment")
            output_path = Path(experiment.get("output") or experiment_dir / f"{experiment_id}.jsonl")
            methods = load_method_configs([str(path) for path in experiment.get("methods", [])])
            runner = ExperimentRunner(
                cases_path=experiment["cases"],
                methods=methods,
                output_path=output_path,
                experiment_id=experiment_id,
                seeds=[int(seed) for seed in experiment.get("seeds", [1])],
                dry_run=True,
                live=False,
                max_cases=experiment.get("max_cases"),
                fail_fast=bool(experiment.get("fail_fast", False)),
            )
            results = runner.run()
            manifest["experiments"].append(
                {
                    "experiment_id": experiment_id,
                    "output": str(output_path),
                    "result_count": len(results),
                    "status_counts": _counts(result.status for result in results),
                }
            )
        except Exception as exc:
            if fail_fast:
                raise
            warnings.append(f"experiment {experiment.get('experiment_id', 'unknown')} failed: {exc}")


def _workflow_state_from_config(workflow: dict[str, Any], rebuild_index: bool) -> dict[str, Any]:
    state = {
        "workflow_run_id": workflow["workflow_run_id"],
        "run_id": workflow.get("run_id") or workflow["workflow_run_id"],
        "case_id": workflow.get("case_id"),
        "method_id": workflow.get("method_id"),
        "domain": workflow.get("domain"),
        "ticker": workflow.get("ticker"),
        "decision_date": workflow.get("decision_date"),
        "task_type": workflow.get("task_type"),
        "manifest_path": workflow.get("manifest"),
        "index_dir": workflow.get("index_dir"),
        "rag_config_path": workflow.get("rag_config"),
        "claims_path": workflow.get("claims"),
        "ledger_dir": workflow.get("ledger_dir"),
        "ledger_config_path": workflow.get("ledger_config", "configs/ledger/default_ledger.yaml"),
        "guardrail_config_path": workflow.get("guardrail_config"),
        "policy_paths": workflow.get("policy_paths") or workflow.get("policies") or [],
        "workflow_config_path": workflow.get("workflow_config"),
        "workflow_output_dir": workflow.get("output_dir"),
        "rebuild_index": bool(rebuild_index or workflow.get("rebuild_index", False)),
        "fail_fast": bool(workflow.get("fail_fast", False)),
    }
    if workflow.get("top_k") is not None:
        state["top_k"] = int(workflow["top_k"])
    if workflow.get("max_retries") is not None:
        state["max_retries"] = int(workflow["max_retries"])
    return state


def _failed_summary(
    benchmark_id: str,
    pack_id: str,
    workflow: dict[str, Any],
    error_message: str,
) -> BenchmarkRunSummary:
    return BenchmarkRunSummary(
        benchmark_id=benchmark_id,
        pack_id=pack_id,
        workflow_run_id=str(workflow.get("workflow_run_id") or "unknown"),
        case_id=workflow.get("case_id"),
        method_id=workflow.get("method_id"),
        domain=workflow.get("domain"),
        ticker=workflow.get("ticker"),
        decision_date=workflow.get("decision_date"),
        task_type=workflow.get("task_type"),
        route_decision="error",
        route_reason=error_message,
        overall_status="error",
        retry_count=0,
        error_count=1,
        metadata={"warnings": [error_message]},
    )


def _counts(values) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[str(value)] = counts.get(str(value), 0) + 1
    return counts


def _count_text(counts: dict[str, int]) -> str:
    if not counts:
        return "none"
    return ",".join(f"{key}={value}" for key, value in sorted(counts.items()))


if __name__ == "__main__":
    raise SystemExit(main())
