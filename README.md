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
| `configs/` | Domain, RAG, ledger, guardrail, workflow, experiment, and benchmark YAML. |
| `data/` | Synthetic sample cases, claims, and RAG sample documents. |
| `docs/` | Architecture, research plan, demo guide, metrics, and release checklist. |
| `scripts/` | Offline build, validation, benchmark, report, and workflow commands. |

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

## Safety Boundaries

- Offline demo commands do not require API keys.
- `.env` is ignored by git and should contain local secrets only.
- Generated outputs are ignored under `results/` and `data/indexes/`.
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
