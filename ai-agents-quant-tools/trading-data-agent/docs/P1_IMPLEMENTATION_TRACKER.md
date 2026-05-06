# Project 1: Trading Data Agent — Implementation Tracker

**Stack**: Python 3.10+ | LangChain | LangGraph | OpenAI Agents SDK | Pandas | NumPy | Plotly | Pydantic | Python-dotenv | Jinja2 | Loguru | Pytest *(FastAPI + React + TypeScript dashboard upgrade planned)*

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
