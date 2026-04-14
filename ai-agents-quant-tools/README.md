# Four AI Agent Projects for Trading Infrastructure

*Leveraging 3+ years of trading tools experience to build the next generation of AI-powered systems*

---

## Why I'm Building These

While my day job is focused on immediate trader needs, I believe the future of quant tools is **AI-powered and autonomous**. So I'm building these 4 projects in my spare time to:

- ✅ Master AI Agent systems and LLM integration
- ✅ Demonstrate how AI can amplify the tools I've built at my investment bank
- ✅ Create a portfolio showing my ability to architect intelligent systems from scratch
- ✅ Prepare for the next evolution of my career in AI × Trading Technology

**Important Note:** These are **personal projects** built independently in my spare time, inspired by real trading workflows but not using any company code or proprietary information.

---

## 🔄 From Trading Tools to AI-Powered Tools

My **3+ years building tools directly for traders and quant teams** gave me deep insight into:

| Trader Pain Point | Tool I Built | How AI Agents Improve It |
|---|---|---|
| **Data quality checks slow down analysis** | Data pipelines + validation | Automated agents detect + fix issues in real-time |
| **Metric calculation takes time** | Calculation tools + workflows | Agent-driven orchestration processes in parallel |
| **"Why did my metric change?" → hours of investigation** | Explainability dashboards | AI agents auto-generate answers + rationales instantly |
| **Manual batch processing every day** | Data pipeline tools | Agents autonomously handle pipeline workflows |

**The Insight:** Most trading tools today are built for *humans to manually operate*. My AI Agent projects are built for *humans to leverage intelligent agents*.

The future of quant tools is **AI-augmented, not human-replaced**. Traders spend time on strategy, agents handle the operational work.

---

## Project Overview

| Project | Complexity | Status |
|---|---|---|
| Trading Data Agent | ⭐⭐⭐⭐ | 🔄 In Progress |
| Quant ETL Agent | ⭐⭐⭐⭐ | ⬜ Not Started |
| Explainability Agent | ⭐⭐⭐⭐⭐ | ⬜ Not Started |
| QuantOps Engine | ⭐⭐⭐⭐⭐ | ⬜ Not Started |

---

## 1️⃣ Trading Data Multi-Agent Assistant

**Tick Replay + Cleaning + Microstructure + SQL Generation + Reporting**

*Evolution of the data pipeline work I've done for trading desks but with AI Agents*

**Purpose**: Automate trading data ingestion, quality assurance, microstructure analysis, and report generation.

**Key Features**:
- Ingest tick data from multiple sources (CSV, Parquet, S3)
- Detect & repair missing ticks, irregular timestamps, data anomalies
- Perform anomaly detection and market event flagging
- Execute tick replay simulations (time-window based)
- Extract microstructure features (imbalance, depth, intensity, bounce)
- Generate SQL for VWAP, OHLC, aggregated bars
- Produce automated daily summaries & HTML reports

**Why I Built This**: In my trading desk work, data quality consumed significant manual effort from traders. This sparked an idea: what if an AI Agent could automate this?

I built this as a **personal side project** to explore how AI Agents can solve real trading workflow problems. It's inspired by the data challenges I see daily at work, but it's my own implementation from scratch — no company code, pure learning and building.

**Agents**: `IngestionAgent` `CleaningAgent` `AnalysisAgent` `ReportingAgent` `PlannerAgent`

**Tech Stack**:
`OpenAI Agents SDK` | `LangGraph` | `LangChain` | `Pandas` | `Jinja2` | `Plotly`

**Architecture**:
```
User Query → PlannerAgent
             ↓
    IngestionAgent → CleaningAgent → AnalysisAgent
             ↓
         ReportingAgent → Final Output
```

📂 **Repository**: [trading-data-agent](https://github.com/rosalynchan/quant-dev-portfolio/tree/main/ai-agents-quant-tools/trading-data-agent)

---

## 2️⃣ Quant ETL Multi-Agent Pipeline

**Drift Detection + Reconciliation + Schema Validation + ETL Orchestration**

*Extension of the data pipeline optimization I've done supporting trading operations*

**Purpose**: Build an intelligent ETL system with validation, drift detection, and reconciliation.

**Key Features**:
- Auto-detect and validate data schema
- Detect statistical drift in data distributions (mean, variance, distribution)
- Reconcile data from multiple sources (T-1 vs T, source vs derived)
- Root cause analysis for reconciliation gaps
- Generate SQL queries for analytics
- Pipeline health reports & ready-for-analysis status

**Why I Built This**: Every day at work, I see quant teams spend hours on manual data validation before analysis. I built this **as a personal project** to demonstrate how multi-agent systems can automate the entire ETL workflow.

It's inspired by real challenges I face in my job — drift detection, reconciliation, data quality, but it's my own independent exploration of how AI Agents can solve these problems at scale.

**Agents**: `SourceAgent` `ValidationAgent` `DriftAgent` `ReconcileAgent` `SQLAgent` `ReportingAgent` `PlannerAgent`

**Tech Stack**:
`LangGraph` | `Pandas` | `Polars` | `SQLite` | `FastAPI` | `Plotly` | `Jinja2` *(React + TypeScript upgrade planned)*

**Architecture**:
```
Data Sources (S3, DB, API)
         ↓
    PlannerAgent
         ↓
SourceAgent | ValidationAgent | DriftAgent | ReconcileAgent
         ↓
    SQLAgent → ReportingAgent
         ↓
    Dashboard Output
```

📂 **Repository**: [quant-etl-agent](https://github.com/rosalynchan/quant-dev-portfolio/tree/main/ai-agents-quant-tools/quant-etl-agent)

---

## 3️⃣ Explainability Agent Engine ⭐

**Rule Builder + Explain Classifier + Rationale NLG + Dashboard**

*Natural evolution of the explainability work I've built for trading metrics — now with AI agents*

**Purpose**: Generate natural language explanations for why trading metrics changed.

**Key Features**:
- Natural language → predicate rule builder agent
- Automatic explained/unexplained classification
- Rationale generation (natural language explanations)
- Rule performance & coverage evaluation
- Trader/desk-level summaries
- Heatmap visualization of unexplained metrics

**Why This Matters**: In my daily work with traders, explaining metric changes quickly is critical. I've built rule-based systems that achieved this, reducing investigation time by **20-30 minutes per trader per day**.

I created this **as a personal side project** to take that concept further with AI Agents — what if agents could automatically generate and refine rules, learn from trader feedback, and continuously improve explanations? This is where I'm most excited about AI's potential in trading technology.

**Agents**: `RuleAgent` `ClassifyAgent` `ExplainAgent` `FeedbackAgent` `ReportAgent`

**Tech Stack**:
`OpenAI Agents SDK` | `Pandas` | `Custom Rule Engine` | `Jinja2` | `Plotly` *(React + TypeScript upgrade planned)*

**Perfect for**:
- Trading metric explainability
- Compliance & audit trails
- Dashboard-driven trader workflows

📂 **Repository**: [explainability-agent](https://github.com/rosalynchan/quant-dev-portfolio/tree/main/ai-agents-quant-tools/explainability-agent)

---

## 4️⃣ QuantOps Agent Engine ⭐ (Capstone)

**The End-to-End Multi-Agent Orchestration System**

*Everything I've built to support traders, now powered by AI Agents*

**Purpose**: Unified platform integrating all three projects into one intelligent system.

**Key Features**:
- Orchestrates all agents from Projects 1-3 via master LangGraph graph
- RESTful API for data and metric operations
- Real-time React dashboard with metrics and explanations
- Complete workflow: Load → Clean → Validate → Analyse → Explain → Report

**Why This Matters**: Over 3+ years, I've built individual tools to support traders — data pipelines, calculation platforms, explainability systems. This **personal capstone project** brings all these threads together: what if one unified AI Agent system could orchestrate everything?

This is my vision for the next evolution of trading tools.

**Agents**: `PlannerAgent` (orchestration) + all agents from Projects 1-3

**Tech Stack**:
`LangGraph` | `OpenAI Agents SDK` | `LangChain` | `FastAPI` | `Pandas` | `Polars` | `PostgreSQL` | `SQLite` | `React` | `TypeScript` | `Plotly` | `Docker`

**Full Architecture**:
```
                        API / Web UI
                             ↓
                        PlannerAgent
                             ↓
        ┌────────────────────────────────────────┐
        │      Multi-Agent Orchestration Layer    │
        └────────────────────────────────────────┘
           ↓              ↓                ↓
      IngestionAgent  CleaningAgent  AnalysisAgent        (P1)
           ↓              ↓                ↓
    SourceAgent  ValidationAgent  DriftAgent  ReconcileAgent  SQLAgent  (P2)
           ↓              ↓                ↓
      RuleAgent  ClassifyAgent  ExplainAgent  FeedbackAgent  (P3)
           ↓              ↓                ↓
                  ReportingAgent
                         ↓
        ┌─────────────────────────────────┐
        │    Dashboard + API Output        │
        │  (JSON, HTML, API endpoints)     │
        └─────────────────────────────────┘
```

📂 **Repository**: [quantops-agent-engine](https://github.com/rosalynchan/quant-dev-portfolio/tree/main/ai-agents-quant-tools/quantops-agent-engine)

---

## Integration Flow

```
Project 1: Data Loading & Cleaning
    ↓
Project 2: Validation & Drift Detection
    ↓
Project 3: Explanation Generation
    ↓
Project 4: Complete Integrated Platform
```

---

## Technology Stack

| Layer | Technology |
|---|---|
| **Agent Frameworks** | LangChain, LangGraph, OpenAI Agents SDK |
| **Language** | Python 3.10+ |
| **Data Processing** | Pandas, NumPy, Polars |
| **Statistical Analysis** | SciPy, Scikit-learn |
| **Databases** | PostgreSQL, SQLite |
| **API** | FastAPI, Uvicorn, Pydantic |
| **Dashboard (P1-P3)** | Plotly, Jinja2 |
| **Dashboard (P4)** | React, TypeScript, Plotly, WebSockets |
| **Testing** | Pytest |
| **Deployment** | Docker, Kubernetes ready |

---

## Project Status

**Current**: P1 actively in development. P2, P3, P4 not yet started.

Core architecture is defined for all four projects. Implementation progressing in phases — code pushed as each phase completes.

**Implementation Timeline**:
```
P1:  ████████ (8w)
P2:          ██████████ (10w)
P3:          ████████ (8w, overlaps P2)
P4:                    ████████████ (12w, starts after P1+P2+P3)
```

- P1: weeks 1–8
- P2 + P3 in parallel: weeks 9–19
- P4: weeks 20–31

**Total**: ~31 weeks / ~7-8 months for complete implementation

---

## Architecture & Design Documentation

Each project includes:

| Document | Purpose |
|---|---|
| **`/docs/architecture.md`** | Full system design, data flow, agent patterns |
| **`/docs/api_reference.md`** | API endpoints, request/response examples |
| **`/docs/design_decisions.md`** | Why we chose X over Y, trade-offs, learnings |
| **`README.md`** | Project overview, agent responsibilities, getting started |

---

## Key Technical Decisions

**Why Multi-Agent Architecture?**
- **Separation of concerns:** Each agent specialises in one domain
- **Composability:** Reuse agents across projects
- **Explainability:** Clear reasoning trail for each decision
- **Resilience:** If one agent fails, others continue

**Why LangGraph + OpenAI Agents SDK?**
- Stateful DAG execution for complex workflows
- Built-in tool-calling for SQL, file I/O, API calls
- Human-in-the-loop capabilities
- Production-ready error handling

**Why Polars + SciPy?**
- Fast, memory-efficient data processing
- Statistical analysis for drift detection (KS test, distribution shifts)
- Seamless integration with NumPy for numerical operations
- Superior to Pandas for large financial datasets

---

## 🎓 Background

**MSc Computing Science** | University of Glasgow, UK (2021–2022)
- Dissertation: *Automation in Quantitative Strategy Systems*
- Core courses: Data Science & Systems, Machine Learning & AI, Information Visualization

**B.Eng Software Engineering** | East China University of Technology, China
- High-distinction grades: Software Engineering (95%), Data Structures & Algorithms (83%), Data Mining & Business Intelligence (89%)

**Industry**: 3+ years at tier-1 investment bank building risk tools, funding optimisation systems, and explainability dashboards for trading desks.

---

**License**: MIT
