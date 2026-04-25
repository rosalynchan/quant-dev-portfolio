# Project 1: Trading Data Agent — Implementation Tracker

**Stack**: Python 3.10+ | LangChain | LangGraph | OpenAI Agents SDK | Pandas | NumPy | Plotly | Pydantic | Python-dotenv | Jinja2 | Loguru | Pytest

---

## Phase 1: Foundation

> Set up logging, config, environment, and the shared state schema that flows through the LangGraph pipeline. BaseAgent defines the interface every agent must follow.

| Task | Component | Notes |
|------|-----------|-------|
| Logger configuration | `src/utils/logger.py` | Loguru setup, log levels, file + console output |
| Config management | `src/utils/config.py` | Load `.env`, OpenAI API key, agent settings |
| Environment template | `.env.example` | OPENAI_API_KEY, LOG_LEVEL, MAX_ITERATIONS |
| Dependencies | `requirements.txt` | Pin all versions: langchain, langgraph, openai, pandas, numpy, plotly, pydantic, python-dotenv, loguru, pytest, jinja2 |
| LangGraph state schema | `src/agents/state.py` | Define `TradingAgentState` — the typed dict that flows between all nodes |
| Base agent class | `src/agents/base_agent.py` | Abstract class: `process()`, `validate_input()`, `run()` |
| Base agent tests | `tests/test_base_agent.py` | Test interface contract |

**Key design decision**: `TradingAgentState` carries all data between agents — raw_df, clean_df, metadata, quality_report, analysis_results, errors. Define this before writing any agent.

---

## Phase 2: Data Ingestion

> Build the tool that loads files, then wrap it in IngestionAgent as the first LangGraph node.

| Task | Component | Notes |
|------|-----------|-------|
| Data loader tool | `src/tools/data_loader.py` | Load CSV, Parquet, Excel → DataFrame + metadata |
| Sample data | `examples/sample_data/sample_ticks.csv` | 1000 rows of synthetic tick data for testing |
| Ingestion agent | `src/agents/ingestion_agent.py` | LangGraph node: reads file path from state, outputs raw_df + metadata |
| Ingestion tests | `tests/test_ingestion_agent.py` | Test all 3 formats, missing file, corrupt file |

---

## Phase 3: Data Cleaning

> Build validation and anomaly detection tools, then wrap in CleaningAgent as second LangGraph node.

| Task | Component | Notes |
|------|-----------|-------|
| Validators tool | `src/tools/validators.py` | Check nulls, duplicates, type mismatches |
| Anomaly detector tool | `src/tools/anomaly_detector.py` | Flag negative prices, zero quantities, outliers |
| Cleaning agent | `src/agents/cleaning_agent.py` | LangGraph node: reads raw_df, outputs clean_df + quality_report |
| Cleaning tests | `tests/test_cleaning_agent.py` | Test each cleaning rule independently |

---

## Phase 4: Data Analysis

> AnalysisAgent uses OpenAI Agents SDK to intelligently decide which metrics to calculate based on the data shape.

| Task | Component | Notes |
|------|-----------|-------|
| Analysis agent | `src/agents/analysis_agent.py` | OpenAI Agent with tools: calculate_vwap, calculate_ohlc, detect_price_jumps, compute_imbalance |
| Analysis tests | `tests/test_analysis_agent.py` | Test each metric calculation with known inputs/outputs |

**Key design decision**: AnalysisAgent is where OpenAI Agents SDK adds value — the LLM decides which analysis tools to call based on the available columns in the data.

---

## Phase 5: Reporting

> ReportingAgent generates the Jinja2 HTML report from all upstream results.

| Task | Component | Notes |
|------|-----------|-------|
| HTML report template | `src/tools/report_template.html` | Jinja2 template: summary, quality metrics, data preview, charts |
| Reporting agent | `src/agents/reporting_agent.py` | LangGraph node: reads analysis_results + quality_report, outputs HTML file |
| Reporting tests | `tests/test_reporting_agent.py` | Test report generated correctly, all sections present |

---

## Phase 6: Orchestration

> Wire all agents into a LangGraph graph. PlannerAgent decides the execution path. TradingDataAssistant is the single entry point.

| Task | Component | Notes |
|------|-----------|-------|
| Planner agent | `src/agents/planner_agent.py` | Determines which nodes to run based on input and state |
| LangGraph graph assembly | `src/agents/graph.py` | Define nodes, edges, conditional routing, compile graph |
| Main orchestrator | `src/main.py` | `TradingDataAssistant` class — public API for the whole system |
| Planner tests | `tests/test_planner_agent.py` | Test routing logic |
| Integration tests | `tests/test_main.py` | End-to-end: CSV in → HTML report out |

**LangGraph flow**:
```
START → PlannerAgent → IngestionAgent → CleaningAgent → AnalysisAgent → ReportingAgent → END
```

---

## Phase 7: Examples & Config

| Task | Component | Notes |
|------|-----------|-------|
| Basic usage example | `examples/basic_usage.py` | Show full pipeline in ~20 lines |
| Package setup | `setup.py` | Package name, version, dependencies |

---

## Phase 8: Documentation

| Task | Component | Notes |
|------|-----------|-------|
| Architecture doc | `docs/architecture.md` | LangGraph state flow diagram, agent responsibilities |
| API reference | `docs/api_reference.md` | TradingDataAssistant public methods, agent interfaces |
| Design decisions | `docs/design_decisions.md` | Why LangGraph, why OpenAI Agents SDK for AnalysisAgent |
| README update | `README.md` | Honest status update reflecting completed phases |
| Code review | Codebase | Check all comments in English, no dead code |

---

## Overall Progress

**Total Items**: 36
**Completed**: 0 (0%)
**In Progress**: 0 (0%)
**Pending**: 34 (100%)

---

## Status Legend

- ⏳ Pending
- 🔄 In Progress
- ✅ Completed
- ⚠️ Blocked

---

**Current Focus**: Phase 1 — Foundation
