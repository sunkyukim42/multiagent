# Reliability-Aware Domain-Specific Multi-Agent RAG System

This repository extends TradingAgents with an offline reliability-aware
research pipeline for domain-specific decision support. The current offline
demo covers synthetic oil and procurement cases and packages the pipeline for
research planning and portfolio review.

The live `python main.py` TradingAgents demo remains separate. The offline demo
does not require API keys and does not call external APIs, OpenAI, LLMs, or
embedding services.

## Quickstart: Offline Demo

Run the full offline benchmark pack:

```bash
python scripts/run_benchmark_pack.py \
  --config configs/benchmarks/task8_full_demo.yaml \
  --output-dir results/benchmark_packs/task8_full_demo \
  --pack-id task8_full_demo \
  --rebuild-index
```

Generate a research-oriented Markdown report:

```bash
python scripts/generate_research_report.py \
  --benchmark-dir results/benchmark_packs/task8_full_demo \
  --output-dir results/reports/task8_research \
  --report-id task8_research
```

Generate a portfolio-oriented Markdown summary:

```bash
python scripts/generate_portfolio_summary.py \
  --benchmark-dir results/benchmark_packs/task8_full_demo \
  --output-dir results/reports/task8_portfolio \
  --report-id task8_portfolio
```

Generated artifacts are ignored by git under `results/` and `data/indexes/`.

## Repository Map

| Path | Purpose |
| --- | --- |
| `tradingagents/` | Original/live TradingAgents implementation and graph. |
| `enterprise_decision_agents/core/` | Domain Registry, run context, claims, and evidence ledger schemas. |
| `enterprise_decision_agents/evaluation/` | API-free experiment runner and metrics. |
| `enterprise_decision_agents/ingestion/` | Offline document parsing and chunking. |
| `enterprise_decision_agents/retrieval/` | Local RAG index and hybrid retrieval. |
| `enterprise_decision_agents/guardrails/` | Deterministic Reliability Guardrails. |
| `enterprise_decision_agents/orchestration/` | Optional offline reliability-aware workflow. |
| `enterprise_decision_agents/reporting/` | Task 8 benchmark and portfolio reporting. |
| `enterprise_decision_agents/presentation/` | Task 10 final package schemas and builder. |
| `enterprise_decision_agents/live/` | Task 11 live case-set and snapshot planning scaffolding. |
| `configs/` | Domain, RAG, ledger, guardrail, workflow, experiment, benchmark, and live YAML. |
| `configs/presentation/` | Final package presentation YAML. |
| `configs/live_experiments/` | Live case panel, provider limits, and snapshot collection YAML. |
| `data/` | Synthetic sample cases, claims, and RAG sample documents. |
| `docs/` | Architecture, research plan, demo guide, metrics, and release checklist. |
| `docs/final/` | Final portfolio and graduate research Markdown assets. |
| `docs/live_quantitative_experiment.md` | Task 11-14 live quantitative experiment roadmap. |
| `scripts/` | Offline build, validation, benchmark, report, workflow, final package, and live case commands. |
| `scripts/generate_final_package.py` | Deterministic Task 10 final package generator. |
| `scripts/build_live_case_set.py` | Deterministic Task 11 live case panel builder. |
| `scripts/collect_live_snapshots.py` | Cache-first Task 11 snapshot planner/collector. |
| `scripts/label_market_outcomes.py` | Cache-only Task 12 market outcome labeler. |
| `scripts/preview_live_prompt_context.py` | Offline Task 13B live prompt context previewer. |
| `scripts/run_live_research_evaluation.py` | Task 13D batch live research evaluation runner. |
| `scripts/summarize_live_experiment.py` | Offline Task 14 live experiment summary and table generator. |

## Task Progression

| Task | Summary |
| --- | --- |
| Task 1 | Stabilized core TradingAgents defaults and API-free smoke checks. |
| Task 2 | Added YAML-backed Domain Registry metadata. |
| Task 3 | Added API-free Experiment Runner and mock methods. |
| Task 4 | Added offline LlamaIndex-based local RAG. |
| Task 5 | Added offline Evidence Ledger. |
| Task 6 | Added deterministic Reliability Guardrails. |
| Task 7 | Added optional offline Reliability Workflow. |
| Task 7.1 | Cleaned workflow config semantics and runtime behavior. |
| Task 8 | Added benchmark/report/portfolio packaging. |
| Task 9 | Added offline research-evaluation tables and aggregation scaffolds. |
| Task 10 | Added final portfolio and graduate research package. |
| Task 11 | Added live case-set and external snapshot collection scaffolding. |
| Task 12 | Added cache-only market outcome labeling. |
| Task 13A | Added LLM output schema, cache, parser, and cost-estimation foundation. |
| Task 13B | Added offline live method matrix and prompt context builder. |
| Task 13C | Added gated OpenAI runner abstraction and deterministic fake runner. |
| Task 13D | Added batch live research evaluation orchestration. |
| Task 14 | Added offline live experiment summary and statistical evaluation. |

## Safety Boundaries

- Offline demo commands do not require API keys.
- `.env` is ignored by git and should contain local secrets only.
- Generated outputs are ignored under `results/`, `data/indexes/`, `data/live_snapshots/`,
  `results/live_labels/`, `results/live_research_eval/`, `results/llm_cache/`,
  `results/live_experiment_summary/`, `results/live_statistical_tests/`, and
  `results/live_kci_tables/`.
- `python main.py` is the separate live TradingAgents demo path.
- Sample outputs are synthetic and illustrative, not paper-ready.
- Reports are not financial, procurement, or legal advice.
- Heuristic groundedness is not semantic entailment.

## Documentation

- [Architecture Overview](docs/architecture_overview.md)
- [Research Plan](docs/research_plan.md)
- [Portfolio Demo](docs/portfolio_demo.md)
- [Evaluation Metrics](docs/evaluation_metrics.md)
- [Research Evaluation Pack](docs/research_evaluation_pack.md)
- [Final Package Docs](docs/final/portfolio_project_summary.md)
- [Live Quantitative Experiment Roadmap](docs/live_quantitative_experiment.md)
- [Release Checklist](docs/release_checklist.md)

## Task 9: Research Evaluation Pack

Task 9 packages the Task 8 benchmark outputs into an offline research-evaluation
scaffold with method metadata, synthetic case-set metadata, ablation
definitions, descriptive bootstrap intervals, and KCI-style Markdown tables.

Run the offline research evaluation:

```bash
python scripts/run_research_evaluation.py \
  --config configs/research/task9_research_eval.yaml \
  --output-dir results/research_eval/task9_demo \
  --evaluation-id task9_demo \
  --run-benchmarks
```

Generate KCI-style tables:

```bash
python scripts/generate_kci_tables.py \
  --evaluation-dir results/research_eval/task9_demo \
  --output-dir results/research_tables/task9_demo \
  --table-id task9_demo
```

These outputs are synthetic and illustrative. They are not paper-ready, not
statistically conclusive, not financial/procurement/legal advice, and heuristic
groundedness is not semantic entailment.

## Task 10: Final Portfolio & Graduate Research Package

Task 10 packages tracked final-facing Markdown docs into an ignored offline
portfolio and graduate research package. It does not call external APIs, run
LLMs, modify the live TradingAgents graph, or generate PDF/PowerPoint assets.
The offline demo does not require API keys, and the live `python main.py` path
remains separate.

Primary Task 10 assets:

- Final docs: `docs/final/`
- Package config: `configs/presentation/final_portfolio_package.yaml`
- Builder package: `enterprise_decision_agents/presentation/`
- CLI script: `scripts/generate_final_package.py`

Generate the final package:

```bash
python scripts/generate_final_package.py \
  --config configs/presentation/final_portfolio_package.yaml \
  --output-dir results/final_packages/task10_final_package \
  --package-id task10_final_package
```

The generated package includes a summary JSON, artifact manifest, README, and
copies of the tracked `docs/final/` Markdown sources. The materials remain
synthetic and illustrative, not paper-ready, not statistically conclusive, not
financial/procurement/legal advice, and heuristic groundedness is not semantic
entailment.

## Task 11: Live Case Set & External Snapshot Collector

Task 11 builds the first live-data scaffold for future quantitative experiments.
It creates a deterministic 10 ticker x 20 date historical case panel and plans
or collects external provider snapshots into a local cache. It does not call
OpenAI, run LLM decisions, execute `python main.py`, or modify the live
TradingAgents graph.

Build the live case panel:

```bash
python scripts/build_live_case_set.py \
  --config configs/live_experiments/live_case_panel_2020_2024.yaml \
  --output-csv data/cases/live_panel_2020_2024.csv \
  --output-jsonl data/cases/live_panel_2020_2024.jsonl \
  --manifest data/cases/live_panel_2020_2024_manifest.json \
  --print-summary
```

Create a snapshot plan without provider API calls:

```bash
python scripts/collect_live_snapshots.py \
  --cases data/cases/live_panel_2020_2024.csv \
  --config configs/live_experiments/snapshot_collection_default.yaml \
  --provider-limits configs/live_experiments/provider_limits.yaml \
  --output-dir data/live_snapshots/task11_plan \
  --collection-report-dir results/live_collection/task11_plan \
  --experiment-id task11_plan \
  --plan-only \
  --max-cases 3 \
  --print-summary
```

Default Task 11 commands do not call APIs. Live provider APIs require explicit
`--allow-live-api`, and repeated experiments should use cached snapshots under
ignored `data/live_snapshots/` paths. Task 12 labels outcomes from cached data;
Task 13 runs controlled LLM decision infrastructure; Task 14 summarizes the
offline outputs descriptively. No performance claim is made from these scaffold
artifacts.

## Task 12: Market Outcome Labeling

Task 12 labels Task 11 cases from locally cached normalized price snapshots
only. It does not read `.env`, call external APIs, call OpenAI, run LLMs,
execute `python main.py`, or modify the live TradingAgents graph. Future price
data is label-only and must not be used as agent input.

By default, labels are benchmark-adjusted against `SPY` using cached price
records. Missing ticker or benchmark data produces `UNKNOWN` labels unless a
policy and CLI override explicitly enable raw-return fallback.

Generate cache-only market outcome labels:

```bash
python scripts/label_market_outcomes.py \
  --cases data/cases/live_panel_2020_2024.csv \
  --snapshot-dir data/live_snapshots/task11_plan \
  --policy configs/live_experiments/labeling_policy.yaml \
  --output-csv data/cases/live_panel_2020_2024_labeled.csv \
  --output-jsonl data/cases/live_panel_2020_2024_labeled.jsonl \
  --manifest data/cases/live_panel_2020_2024_label_manifest.json \
  --report-dir results/live_labels/live_panel_2020_2024 \
  --label-run-id live_panel_2020_2024 \
  --max-cases 5 \
  --print-summary
```

Task 12 labels are synthetic/illustrative research scaffolding, not paper-ready,
not statistically conclusive, not financial/procurement/legal advice, and not a
performance claim. Heuristic groundedness remains separate from semantic
entailment. Task 13 builds controlled LLM decision infrastructure, and Task 14
remains the statistical evaluation layer.

## Task 13A: LLM Output Schema, Cache, Parser, And Costing

Task 13A adds only the foundation for future cached LLM decision experiments:
LLM output schemas, deterministic cache keys, JSONL cache helpers, a
BUY/HOLD/SELL/UNKNOWN decision parser, and cost-estimation helpers driven by
`configs/live_experiments/openai_runtime.yaml`.

It does not call OpenAI, build prompts, run LLMs, execute provider APIs, run
`python main.py`, modify the live TradingAgents graph, or perform statistical
evaluation. Generated future LLM caches and live research outputs are ignored
under `results/llm_cache/` and `results/live_research_eval/`. Task 13B builds
prompts, Task 13C adds the explicit OpenAI runner, Task 13D adds batch live
evaluation, and Task 14 remains the statistical evaluation layer.

## Task 13B: Live Method Matrix And Prompt Context Builder

Task 13B adds an offline prompt/input construction layer for controlled future
LLM experiments. It defines six method variants in
`configs/live_experiments/live_method_matrix.yaml`, builds deterministic prompt
contexts from Task 11 cases and local cached snapshot metadata, and writes safe
previews without calling OpenAI, provider APIs, embeddings, `python main.py`, or
the live TradingAgents graph.

Preview one prompt context:

```bash
python scripts/preview_live_prompt_context.py \
  --cases data/cases/live_panel_2020_2024.csv \
  --case-id XOM_2020_03_31 \
  --method-matrix configs/live_experiments/live_method_matrix.yaml \
  --method-id full_reliability_workflow \
  --snapshot-dir data/live_snapshots/task11_plan \
  --labeled-cases data/cases/live_panel_2020_2024_labeled.csv \
  --seed 1 \
  --output-json results/live_research_eval/task13b_preview/full_prompt.json \
  --output-md results/live_research_eval/task13b_preview/full_prompt.md \
  --print-summary
```

Task 12 labels and future returns are excluded from prompt text and messages.
The prompt preview is synthetic/illustrative research scaffolding, not
paper-ready, not statistically conclusive, not financial/procurement/legal
advice, and heuristic groundedness is not semantic entailment. Task 13C adds
the explicit OpenAI runner, Task 13D adds batch live evaluation, and Task 14
performs statistical evaluation.

## Task 13C: OpenAI Runner Safety Layer

Task 13C adds only the runner abstraction for future LLM experiments:
request/response schemas, a deterministic fake runner for tests, explicit live
OpenAI gating, cost and call caps, and conversion into Task 13A
`LLMDecisionOutput` records. Default behavior refuses live OpenAI calls.

The real OpenAI path requires an explicit future live flag and `OPENAI_API_KEY`
in the local environment. Key values are never printed or stored. Tests use the
fake runner and guardrail responses, not paid API calls. Task 13D uses this
runner for batch orchestration, and Task 14 remains the statistical evaluation
layer. Task 13C makes no performance claim.

## Task 13D: Batch Live Research Evaluation Runner

Task 13D runs controlled `case x method x seed` decision batches using Task
13B prompt construction, Task 13A cache/output schemas, and Task 13C fake or
gated OpenAI runners. Defaults remain API-free and cache-only. The fake-runner
mode is intended for offline validation and writes ignored outputs under
`results/live_research_eval/` plus cache rows under `results/llm_cache/`.

Run a safe fake-runner batch:

```bash
python scripts/run_live_research_evaluation.py \
  --config configs/live_experiments/live_research_eval_default.yaml \
  --cases data/cases/live_panel_2020_2024.csv \
  --labeled-cases data/cases/live_panel_2020_2024_labeled.csv \
  --snapshot-dir data/live_snapshots/task11_plan \
  --method-matrix configs/live_experiments/live_method_matrix.yaml \
  --openai-runtime configs/live_experiments/openai_runtime.yaml \
  --output-dir results/live_research_eval/task13d_fake \
  --cache-dir results/llm_cache/task13d_fake \
  --evaluation-id task13d_fake \
  --fake-runner \
  --fake-action BUY \
  --max-cases 2 \
  --max-methods 2 \
  --seeds 1 \
  --print-summary
```

Task 13D excludes Task 12 labels, returns, target dates, future prices, and
label statuses from prompt text and messages. Live OpenAI requires the explicit
`--allow-live-openai` flag plus run caps, and Task 14 is required before any
statistical evaluation or performance claim.

## Task 14: Live Experiment Summary & Statistical Evaluation

Task 14 reads Task 13D decision outputs and Task 12 labels offline. It computes
descriptive method metrics, paired comparisons, bootstrap confidence intervals,
McNemar/Wilcoxon test artifacts, and KCI-style Markdown/CSV tables. It does not
call OpenAI, provider APIs, embeddings, `python main.py`, or the live
TradingAgents graph.

Summarize a safe fake-runner validation batch:

```bash
python scripts/summarize_live_experiment.py \
  --config configs/live_experiments/live_summary_default.yaml \
  --decisions results/live_research_eval/task14_fake_input/decisions.jsonl \
  --llm-outputs results/llm_cache/task14_fake_input/llm_outputs.jsonl \
  --labeled-cases data/cases/live_panel_2020_2024_labeled.csv \
  --output-dir results/live_experiment_summary/task14_fake_summary \
  --table-dir results/live_kci_tables/task14_fake_summary \
  --summary-id task14_fake_summary \
  --baseline-method-id baseline_tradingagents_like \
  --comparison-method-ids domain_agent_only \
  --horizons 63,126 \
  --bootstrap-iterations 200 \
  --bootstrap-seed 42 \
  --allow-fake-runner-outputs \
  --print-summary
```

Fake-runner outputs are pipeline validation only, UNKNOWN labels may dominate
until real cached snapshots are collected, and small samples are not paper-ready
or statistically conclusive. Task 14 tables make no performance claim and do not
provide financial/procurement/legal advice.

## Legacy TradingAgents Notes

**<!--실행 파일>**
./main.py 실행 (python main.py)
**ticker 변경 및 날짜 변경 원할 시, main.py 29line 수정하기**
**석유 회사 리스트: XOM(ExxonMobil), CVX(Chevron)

**<!--프롬프트 관련 경로 -->**
**프롬프트를 고도화할때는, 웬만해서 system prompt(instruction)는 수정하지 말고, prompt를 수정하는 것을 추천**
🟪 **1. analyst**
🟦 1) 뉴스 분석가: tradingagents/agents/analysts/news_nalyst.py  
해당 파일의 prompt(23lines~)

🟦 2) 마켓 분석가: tradingagents/agents/analysts/market_analyst.py  
해당 파일의 prompt(52lines~)

🟦 3) 소셜 미디어 분석가: tradingagents/agents/analysts/social_media_analyst.py  
해당 파일의 prompt(26lines~)

🟦 4) 거시경제 분석가(원유가격포함): tradingagents/agents/analysts/macro_analyst.py  
해당 파일의 prompt(33lines~)

🟦 5) 기업 기초 분석가: tradingagents/agents/analysts/fundamental_analyst.py  
해당 파일의 prompt(30lines~)

🟪 **2. researchers**
🟦 6) 토론 에이전트: tradingagents/agents/researchers/  
해당 파일의 prompt(26lines~)

🟪 **3. Trader**
🟦 7) Trader 에이전트: tradingagents/agents/trader/trader.py
해당 파일의 promt(34line)

🟪 **4. risk management**
🟦 8) aggresive debater 에이전트: tradingagents/agents/risk_mgmt/aggresive_dabator.py
해당 파일의 prompt(22lines~)

🟦 9) conservative debater 에이전트: tradingagents/agents/risk_mgmt/conservative_dabator.py
해당 파일의 prompt(23lines~)

🟦 10) neutral_debator 에이전트: tradingagents/agents/risk_mgmt/neutral_dabator.py
해당 파일의 prompt(21lines~)

🟪 **4. manager**
🟦 11) research mangagber 에이전트: tradingagents/agents/managers/research_manager.py
해당 파일의 prompt(22lines~)

🟦 12) risk manager 에이전트: tradingagents/agents/managers/risk_manager.py
해당 파일의 prompt(26lines~)



**<!--API KEY 관리-->**
.env 파일에서 관리

**<!--API I/O 명세 -->**
🟪 **1. core_stock_tools**
🟦 1) get_stock_data  
"purpose": "지정한 종목(symbol)의 기간(start_date~end_date) 동안 주가 OHLCV 데이터를 조회",  
"inputs": {  
"symbol": {"type": "string","description": "티커 심볼"},  
"start_date": {"type": "string(YYYY-MM-DD)","description": "조회 시작일"},  
"end_date": {"type": "string(YYYY-MM-DD)","description": "조회 종료일"}  
},  
"response": {"type": "string","format": "포맷된 데이터프레임 문자열","schema_hint": {"index": "date (YYYY-MM-DD)","columns": ["open","high","low","close","volume"]}},  
"notes": ["OHLCV(시가, 고가, 저가, 종가, 거래량) 반환","반환형은 문자열이지만 내용은 표 형태의 시계열 데이터"]

🟪 **2. fundamental_data_tools**  
🟦 2) get_fundamentals  
"purpose": "지정한 종목의 포괄적 펀더멘털 리포트 조회",  
"inputs": {  
"ticker": { "type": "string", "description": "티커 심볼" },  
"curr_date": { "type": "string(YYYY-MM-DD)", "description": "거래 기준일" }  
},  
"response": {"type": "string","format": "포맷된 텍스트/표 리포트","schema_hint": ["회사 개요 / 섹터","시가총액, 주식수","밸류에이션(PE, PB, PS 등)","수익성(마진, ROE/ROA)","성장성(매출/이익 YoY)","재무안정성(부채비율 등)"]}

🟦 3) get_balance_sheet  
"purpose": "대차대조표(재무상태표) 데이터 조회",  
"inputs": {  
"ticker": { "type": "string", "description": "티커 심볼" },  
"freq": { "type": "string", "enum": ["annual", "quarterly"], "default": "quarterly", "description": "보고 주기" },  
"curr_date": { "type": "string(YYYY-MM-DD) | null", "default": null, "description": "거래 기준일 (선택)" }  
},  
"response": {"type": "string","format": "포맷된 텍스트/표 리포트","schema_hint": ["자산: 유동/비유동","부채: 유동/비유동","자본: 자본총계, 이익잉여금"]}

🟦 4) get_cashflow"  
"purpose": "현금흐름표 데이터 조회",  
"inputs": {  
"ticker": { "type": "string", "description": "티커 심볼" },  
"freq": { "type": "string", "enum": ["annual", "quarterly"], "default": "quarterly", "description": "보고 주기" },  
"curr_date": { "type": "string(YYYY-MM-DD) | null", "default": null, "description": "거래 기준일 (선택)" }  
},  
"response": {"type": "string","format": "포맷된 텍스트/표 리포트","schema_hint": ["영업활동CF","투자활동CF","재무활동CF","현금 및 현금성자산 증감"]}

🟦 5) get_income_statement"  
"purpose": "손익계산서 데이터 조회",  
"inputs": {  
"ticker": { "type": "string", "description": "티커 심볼" },  
"freq": { "type": "string", "enum": ["annual", "quarterly"], "default": "quarterly", "description": "보고 주기" },  
"curr_date": { "type": "string(YYYY-MM-DD) | null", "default": null, "description": "거래 기준일 (선택)" }  
},  
"response": {"type": "string","format": "포맷된 텍스트/표 리포트","schema_hint": ["매출액","매출총이익, 영업이익","순이익","EPS 등"]}

🟪 **3. macro_data_tools**  
🟦 6) get_macro_data"  
"purpose": "지정한 기간 동안 FRED 거시경제 시계열(FEDFUNDS, UNRATE, CPIAUCSL, GDP, DCOILWTICO 등)을 조회하여 스냅샷(Markdown)으로 반환",  
"inputs": {  
"series_ids": {"type": "array<string>","description": "FRED 시리즈 ID 목록 (예: ['FEDFUNDS','UNRATE','CPIAUCSL','GDP','DCOILWTICO'])","default": null},  
"start_date": {"type": "string(YYYY-MM-DD) | null","description": "조회 시작일 (기본: 약 6개월 전)","default": null},  
"end_date": {"type": "string(YYYY-MM-DD) | null","description": "조회 종료일 (기본: 오늘)","default": null},  
"frequency": {"type": "string | null","enum": ["d", "w", "m", "q", null],"description": "리샘플링 주기 (기본: 원본 주기 사용)","default": null}  
},  
"response": {"type": "string","format": "JSON 형식"},

🟪 **4. news_data_tools**
🟦 7) get_news  
"purpose": "지정 티커의 기간별 뉴스 데이터 조회",  
"inputs": {  
"ticker": { "type": "string", "description": "티커 심볼" },  
"start_date": { "type": "string(YYYY-MM-DD)", "description": "조회 시작일" },  
"end_date": { "type": "string(YYYY-MM-DD)", "description": "조회 종료일" }  
},  
"response": {"type": "string","format": "포맷된 뉴스 문자열(기사 목록/요약 등)"}

🟦 8) get_global_news  
"purpose": "전세계 범위의 최신 뉴스 조회",  
"inputs": {  
"curr_date": { "type": "string(YYYY-MM-DD)", "description": "기준일" },  
"look_back_days": { "type": "integer", "default": 7, "description": "과거 조회 일수" },  
"limit": { "type": "integer", "default": 5, "description": "최대 기사 수" }  
},  
"response": {"type": "string","format": "포맷된 글로벌 뉴스 문자열(기사 목록/요약 등)"}

🟦 9) get_insider_sentiment  
"purpose": "특정 기업의 내부자(Insider) 심리/평판 지표 조회",  
"inputs": {  
"ticker": { "type": "string", "description": "티커 심볼" },  
"curr_date": { "type": "string(YYYY-MM-DD)", "description": "기준일" }  
},  
"response": {"type": "string","format": "포맷된 내부자 심리 리포트 문자열"}

🟦 10) get_insider_transactions  
"purpose": "특정 기업의 내부자 거래 내역 조회",  
"inputs": {  
"ticker": { "type": "string", "description": "티커 심볼" },  
"curr_date": { "type": "string(YYYY-MM-DD)", "description": "기준일" }  
},  
"response": {"type": "string","format": "포맷된 내부자 거래 리포트 문자열"}

🟪 **5. technical_indicators_tool**  
🟦 11) get_indicators  
"purpose": "지정 티커의 특정 기술지표 분석/리포트를 조회",  
"inputs": {  
"symbol": { "type": "string", "description": "티커 심볼 (예: AAPL, TSM)" },  
"indicator": { "type": "string", "description": "조회할 기술지표 이름(문자열)" },  
"curr_date": { "type": "string(YYYY-MM-DD)", "description": "거래 기준일" },  
"look_back_days": { "type": "integer", "default": 30, "description": "과거 조회 일수" }  
},  
"response": {"type": "string","format": "포맷된 데이터프레임/리포트 문자열","schema_hint": "지표별 계산 결과와 요약(정확한 필드는 벤더 구현에 따름)"}
## Task 1: Stabilization Checks

Run the lightweight stabilization tests without live API calls:

```bash
pytest
```

Run the API-free smoke test:

```bash
python scripts/smoke_test.py
```

Run `python main.py` for the live XOM demo when the required API keys are configured in `.env`.

This stabilization task does not implement Domain Registry, RAG, Evidence Ledger,
or Guardrails.

## Task 2: Domain Registry

The Domain Registry loads lightweight YAML metadata for supported decision
domains without changing the current LangGraph workflow or calling external APIs.
Domain configs live in `configs/domains/` and currently include `oil`,
`semiconductor`, and `procurement`.

Validate domain configs:

```bash
python scripts/validate_domains.py
```

Check required environment variable presence without printing secret values:

```bash
python scripts/validate_domains.py --check-env
```

`.env` keys are optional for tests and validation. They are required only for
live API-backed demos such as `python main.py`.

This task does not implement RAG, Evidence Ledger, Guardrails, Experiment Runner,
or new orchestration.

## Task 3: Experiment Runner

The Experiment Runner provides an API-free mock evaluation path by default. It
runs cases x methods x seeds, writes JSONL results incrementally under
`results/`, and summarizes aggregate metrics by method.

Run the mock sample experiment:

```bash
python scripts/run_experiment.py \
  --cases data/cases/energy_decision_cases_sample.csv \
  --methods configs/experiments/mock_baseline.yaml \
  --output results/task3_sample_results.jsonl \
  --seeds 1,2 \
  --dry-run
```

Summarize generated results:

```bash
python scripts/summarize_results.py \
  --results results/task3_sample_results.jsonl \
  --output results/task3_sample_summary.md
```

Live TradingAgents experiment configs are loadable, but execution requires the
explicit `--live` flag and the required API keys in `.env`. Dry-run and mock
experiments do not call external APIs or print secret values.

This task does not implement RAG, LlamaIndex, Evidence Ledger, Guardrails, or
workflow rewrites.

## Task 4: LlamaIndex-based Chunking and Advanced RAG

Task 4 adds an offline local RAG layer for synthetic, non-confidential domain
documents. It builds retrievable chunk candidates with LlamaIndex core
abstractions, stores generated indexes under `data/indexes/`, and supports
metadata-aware and decision-date-filtered retrieval.

Build the sample local index:

```bash
python scripts/build_rag_index.py \
  --manifest data/raw/rag_samples/documents_manifest.csv \
  --config configs/rag/default_rag.yaml \
  --output-dir data/indexes/task4_sample \
  --index-id task4_sample \
  --rebuild
```

Query the sample index:

```bash
python scripts/query_rag.py \
  --index-dir data/indexes/task4_sample \
  --query "oil inventory demand recovery XOM" \
  --domain oil \
  --ticker XOM \
  --decision-date 2020-11-19 \
  --top-k 3
```

The build and query scripts are offline by default: they do not call external
APIs, OpenAI embeddings, or live TradingAgents graph code. Generated indexes are
ignored by git except `data/indexes/.gitkeep`.

Task 4 is not an Evidence Ledger. It does not implement claim-evidence mapping,
Guardrails, ReliabilityReport, vector databases, RAGAS/TruLens evaluation, or
LangGraph workflow changes. Task 5 will add the Evidence Ledger layer.

## Task 5: Evidence Ledger

Task 5 adds an offline Evidence Ledger for converting local RAG retrieval results
and structured mock claims into auditable evidence records, claim records, and
claim-evidence links. Sample claims are synthetic, illustrative, and
non-confidential.

Build the sample RAG index first:

```bash
python scripts/build_rag_index.py \
  --manifest data/raw/rag_samples/documents_manifest.csv \
  --config configs/rag/default_rag.yaml \
  --output-dir data/indexes/task4_sample \
  --index-id task4_sample \
  --rebuild
```

Build an oil sample ledger:

```bash
python scripts/build_evidence_ledger.py \
  --index-dir data/indexes/task4_sample \
  --claims data/ledger_samples/mock_oil_agent_claims.jsonl \
  --output-dir results/ledgers/task5_oil_demo \
  --run-id task5_oil_demo \
  --case-id XOM_2020_11_19 \
  --method-id mock_rag_ledger \
  --domain oil \
  --ticker XOM \
  --decision-date 2020-11-19 \
  --task-type investment \
  --top-k 2
```

Inspect the generated ledger:

```bash
python scripts/inspect_evidence_ledger.py \
  --ledger-dir results/ledgers/task5_oil_demo \
  --show-claims \
  --show-evidence \
  --show-links \
  --max-items 5
```

Generated ledgers are ignored under `results/ledgers/`. The ledger records
evidence and mappings only; it does not score groundedness, hallucination risk,
citation coverage, temporal leakage, policy compliance, or reliability. Those
checks belong to later tasks.

## Task 6: Reliability Guardrails

Task 6 evaluates offline Evidence Ledger outputs with deterministic checks for
citation coverage, temporal validity, heuristic groundedness, policy compliance,
numeric traceability, and simple consistency. It is not an LLM judge and does not
modify the live TradingAgents graph.

Build the sample ledger first, then run guardrails:

```bash
python scripts/run_guardrails.py \
  --ledger-dir results/ledgers/task5_oil_demo \
  --config configs/guardrails/default_guardrails.yaml \
  --policy configs/policies/default_policy.yaml \
  --policy configs/policies/investment_policy.yaml \
  --output-dir results/reliability/task5_oil_demo \
  --print-summary
```

Inspect the generated ReliabilityReport:

```bash
python scripts/inspect_reliability_report.py \
  --report results/reliability/task5_oil_demo/reliability_report.json \
  --show-findings \
  --max-items 10
```

Generated reliability reports are ignored under `results/reliability/`. The
checks are deterministic heuristics, not semantic entailment, legal advice,
financial advice, or procurement advice. Task 7 will add LangGraph routing or
human-review workflows that consume ReliabilityReports.

## Task 7: Reliability-Aware LangGraph Workflow

Task 7 adds an optional offline LangGraph workflow that orchestrates local RAG
indexing, Evidence Ledger construction, Reliability Guardrails, and deterministic
routing. It does not replace `python main.py`, modify the live TradingAgents
graph, or call external APIs.

Run the sample oil workflow:

```bash
python scripts/run_reliability_workflow.py \
  --workflow-run-id task7_oil_demo \
  --run-id task7_oil_demo \
  --case-id XOM_2020_11_19 \
  --method-id mock_reliability_workflow \
  --domain oil \
  --ticker XOM \
  --decision-date 2020-11-19 \
  --task-type investment \
  --manifest data/raw/rag_samples/documents_manifest.csv \
  --index-dir data/indexes/task4_sample \
  --rag-config configs/rag/default_rag.yaml \
  --claims data/ledger_samples/mock_oil_agent_claims.jsonl \
  --ledger-dir results/ledgers/task7_workflow_oil_demo \
  --guardrail-config configs/guardrails/default_guardrails.yaml \
  --policy configs/policies/default_policy.yaml \
  --policy configs/policies/investment_policy.yaml \
  --workflow-config configs/workflows/default_reliability_workflow.yaml \
  --output-dir results/workflows/task7_oil_demo \
  --top-k 2 \
  --max-retries 1
```

Inspect the workflow artifacts:

```bash
python scripts/inspect_workflow_run.py \
  --workflow-dir results/workflows/task7_oil_demo \
  --show-routing \
  --show-final-report \
  --show-human-review \
  --max-items 10
```

Routes are `final_report`, `retry`, `human_review`, or `stop`, based only on
local ReliabilityReports and deterministic thresholds. Generated workflow
artifacts are ignored under `results/workflows/`. Task 8 or later may integrate
ReliabilityReports with live agents if needed.

Workflow config files can provide safe defaults such as `domain`, `ticker`,
`task_type`, `top_k`, and `max_retries`; explicit CLI or state values override
those defaults. Final workflow state and artifact summaries are always persisted
for inspection. `store_human_review_packet` and `store_final_report` control
whether those optional generated files are written.

## Task 8: Offline Research Benchmark And Portfolio Demo Packaging

Task 8 packages the offline pipeline into reproducible benchmark and reporting
artifacts for research planning and portfolio demos. It reuses the dry-run
Experiment Runner, local RAG, Evidence Ledger, Reliability Guardrails, and
reliability-aware workflow. It does not call external APIs, OpenAI, embeddings,
or live TradingAgents graph code.

Run the combined offline demo pack:

```bash
python scripts/run_benchmark_pack.py \
  --config configs/benchmarks/task8_full_demo.yaml \
  --output-dir results/benchmark_packs/task8_full_demo \
  --pack-id task8_full_demo \
  --rebuild-index
```

Generate a research-oriented Markdown report:

```bash
python scripts/generate_research_report.py \
  --benchmark-dir results/benchmark_packs/task8_full_demo \
  --output-dir results/reports/task8_research \
  --report-id task8_research
```

Generate a portfolio-oriented Markdown summary:

```bash
python scripts/generate_portfolio_summary.py \
  --benchmark-dir results/benchmark_packs/task8_full_demo \
  --output-dir results/reports/task8_portfolio \
  --report-id task8_portfolio
```

Generated benchmark packs are ignored under `results/benchmark_packs/`, and
generated reports are ignored under `results/reports/`. The sample outputs are
synthetic and illustrative, not paper-ready, financial advice, or
procurement advice. Architecture and demo notes live under `docs/`.
