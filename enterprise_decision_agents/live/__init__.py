"""Task 11-15A live case-set, snapshot, label, prompt, LLM-output, summary, and pilot scaffolding."""

from .case_schema import LiveCaseError, LiveCaseRecord
from .label_schema import LabelManifest, MarketOutcomeLabel
from .live_experiment_summary import (
    LiveExperimentSummaryError,
    LiveExperimentSummaryResult,
    LiveSummaryConfig,
    load_live_summary_config,
    run_live_experiment_summary,
)
from .live_method_runner import CaseLabelSummary, LiveMethodRunResult, run_live_method
from .live_metrics import MethodMetrics, compute_method_metrics
from .live_research_runner import (
    LiveResearchEvaluationConfig,
    LiveResearchRunSummary,
    LiveResearchRunnerError,
    load_live_research_evaluation_config,
    run_live_research_evaluation,
)
from .live_result_tables import render_live_result_tables
from .live_run_report import LiveRunReportError, render_live_run_report, write_live_run_report
from .live_statistical_tests import bootstrap_mean_ci, mcnemar_test, wilcoxon_signed_rank_test
from .llm_output_schema import LLMDecisionOutput, LiveDecisionRecord, LiveEvaluationManifest
from .llm_runner_schema import LLMRunnerRequest, LLMRunnerResponse, LLMRunnerSchemaError
from .method_matrix import LiveMethodMatrix, LiveMethodMatrixError, LiveMethodSpec
from .openai_runner import FakeLLMRunner, OpenAIRunner, OpenAIRunnerConfig, OpenAIRunnerError
from .prompt_context_schema import PromptBuildInput, PromptBuildResult, PromptContextSchemaError, PromptEvidenceItem
from .snapshot_schema import ProviderRequest, SnapshotManifest, SnapshotRecord, SnapshotSchemaError
from .snapshot_quality import (
    SnapshotQualityError,
    SnapshotQualityReport,
    SnapshotQualityResult,
    inspect_snapshot_quality,
    render_snapshot_quality_markdown,
)

__all__ = [
    "LabelManifest",
    "CaseLabelSummary",
    "LLMDecisionOutput",
    "LLMRunnerRequest",
    "LLMRunnerResponse",
    "LLMRunnerSchemaError",
    "LiveCaseError",
    "LiveCaseRecord",
    "LiveDecisionRecord",
    "LiveEvaluationManifest",
    "LiveExperimentSummaryError",
    "LiveExperimentSummaryResult",
    "LiveMethodRunResult",
    "LiveMethodMatrix",
    "LiveMethodMatrixError",
    "LiveMethodSpec",
    "LiveResearchEvaluationConfig",
    "LiveResearchRunSummary",
    "LiveResearchRunnerError",
    "LiveRunReportError",
    "LiveSummaryConfig",
    "MarketOutcomeLabel",
    "MethodMetrics",
    "FakeLLMRunner",
    "OpenAIRunner",
    "OpenAIRunnerConfig",
    "OpenAIRunnerError",
    "PromptBuildInput",
    "PromptBuildResult",
    "PromptContextSchemaError",
    "PromptEvidenceItem",
    "ProviderRequest",
    "SnapshotManifest",
    "SnapshotQualityError",
    "SnapshotQualityReport",
    "SnapshotQualityResult",
    "SnapshotRecord",
    "SnapshotSchemaError",
    "bootstrap_mean_ci",
    "compute_method_metrics",
    "load_live_summary_config",
    "load_live_research_evaluation_config",
    "mcnemar_test",
    "inspect_snapshot_quality",
    "render_snapshot_quality_markdown",
    "render_live_result_tables",
    "render_live_run_report",
    "run_live_method",
    "run_live_experiment_summary",
    "run_live_research_evaluation",
    "wilcoxon_signed_rank_test",
    "write_live_run_report",
]
