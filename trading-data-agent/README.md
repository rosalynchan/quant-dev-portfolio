# Project 1: Trading Data Multi-Agent Assistant

## Project Overview

**Purpose**: Automate trading data ingestion, quality assurance, microstructure analysis, and report generation using multi-agent AI system.

**Inspired by**: Real workflow challenges at tier-1 investment banks where traders spend hours on manual data quality checks.

**Personal Project**: Built independently in spare time. Not using any proprietary company code.

---

## Key Requirements

### Functional Requirements

#### 1. Data Ingestion
- Load trading tick data from multiple sources (CSV, Parquet, Excel)
- Support automatic data type detection
- Extract metadata (row count, columns, data types)
- Handle missing files gracefully

#### 2. Data Quality & Cleaning
- Detect and remove missing values
- Identify and eliminate duplicate records
- Detect data type inconsistencies
- Flag anomalies (negative prices, zero quantities, etc.)
- Generate quality metrics report

#### 3. Data Analysis
- Calculate microstructure features (VWAP, OHLC, imbalance, depth)
- Perform tick replay simulation
- Generate statistical summaries
- Detect price jumps and unusual patterns

#### 4. Reporting
- Generate HTML reports with visualizations
- Include data summary statistics
- Display quality metrics
- Create searchable data previews
- Export to multiple formats

### Technical Requirements

- **Multi-Agent Architecture**: Separate agents for different tasks
- **Error Handling**: Graceful error handling and logging
- **Testing**: Unit tests for each component
- **Documentation**: Clear code documentation and usage examples
- **Extensibility**: Easy to add new agents and features

---

## System Architecture

```
User Input (data source)
    ↓
┌─────────────────────────────┐
│   TradingDataAssistant      │ (Main Orchestrator)
│   Coordinates all agents    │
└─────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────┐
│             Multi-Agent Pipeline                 │
├─────────────────────────────────────────────────┤
│ IngestionAgent     → Loads data from files      │
│ CleaningAgent      → Handles quality checks     │
│ AnalysisAgent      → Calculates metrics         │
│ ReportingAgent     → Generates HTML reports     │
└─────────────────────────────────────────────────┘
    ↓
  Output: Clean data + Quality report + HTML report
```

---

## Project Structure

```
trading-data-agent/
├── src/
│   ├── agents/              # Agent implementations
│   │   ├── base_agent.py
│   │   ├── ingestion_agent.py
│   │   ├── cleaning_agent.py
│   │   ├── analysis_agent.py
│   │   ├── reporting_agent.py
│   │   └── planner_agent.py
│   ├── tools/               # Utility functions
│   │   ├── data_loader.py
│   │   ├── validators.py
│   │   └── anomaly_detector.py
│   ├── utils/               # Configuration and logging
│   │   ├── logger.py
│   │   └── config.py
│   └── main.py              # Entry point
├── tests/
│   ├── test_agents.py
│   ├── test_tools.py
│   └── fixtures/
├── docs/
│   ├── architecture.md
│   ├── api_reference.md
│   └── design_decisions.md
├── examples/
│   ├── basic_usage.py
│   └── sample_data/
├── README.md
├── requirements.txt
├── setup.py
├── .env.example
├── .gitignore
└── LICENSE
```

---

## Agent Responsibilities

### BaseAgent (Abstract Class)
- **Purpose**: Define common interface for all agents
- **Key Methods**:
  - `__init__(name, description)` - Initialize agent
  - `process(input_data)` - Core processing logic
  - `validate_input(data)` - Input validation

### IngestionAgent
- **Input**: File path (CSV, Parquet, Excel)
- **Output**: Pandas DataFrame + metadata
- **Tasks**:
  - Detect file format automatically
  - Read data into memory
  - Extract schema information
  - Return row/column counts

### CleaningAgent
- **Input**: Raw DataFrame
- **Output**: Clean DataFrame + quality report
- **Tasks**:
  - Handle missing values
  - Remove duplicate rows
  - Fix data types
  - Detect anomalies (negative prices, zero quantities, etc.)

### AnalysisAgent
- **Input**: Clean DataFrame
- **Output**: Analysis results with metrics
- **Tasks**:
  - Calculate VWAP, OHLC, spreads
  - Detect price jumps
  - Compute order book imbalance
  - Generate statistical summaries

### ReportingAgent
- **Input**: Analyzed data + quality metrics
- **Output**: HTML report file
- **Tasks**:
  - Create professional HTML report
  - Include data preview tables
  - Display charts and visualizations
  - Embed quality metrics

### PlannerAgent
- **Purpose**: Orchestrate workflow
- **Tasks**:
  - Determine processing steps needed
  - Define agent execution order
  - Handle conditional routing

---

## Data Flow Example

```
Input: "trading_ticks.csv"
    ↓
IngestionAgent
  - Loads 10,000 rows × 8 columns
  - Detects columns: timestamp, symbol, price, quantity, bid, ask, bid_size, ask_size
    ↓
CleaningAgent
  - Removes 50 rows with missing values
  - Removes 30 duplicate rows
  - Detects 5 negative prices (anomalies)
  - Final: 9,920 clean rows
    ↓
AnalysisAgent
  - Calculates VWAP: $150.45
  - Detects 3 price jumps > 0.5%
  - Computes bid-ask spread statistics
    ↓
ReportingAgent
  - Generates: report_20240101_093000.html
  - Includes: summary, quality metrics, data preview, charts
    ↓
Output: Clean data + HTML report
```

---

## Technology Stack

| Component | Technology |
|-----------|------------|
| Data Processing | Pandas, NumPy |
| Agent Framework | LangChain, Custom classes |
| Configuration | Pydantic, Python-dotenv |
| Logging | Loguru |
| Testing | Pytest |
| Web Framework | FastAPI (future) |
| Reports | Jinja2 templates, HTML/CSS |

---

## Success Metrics

- [x] Multi-agent system with clear separation of concerns
- [x] Handle multiple data formats (CSV, Parquet, Excel)
- [x] Detect and report data quality issues
- [x] Generate professional HTML reports
- [x] Comprehensive error handling and logging
- [x] Full test coverage for core components
- [x] Clear documentation and examples

---

## Future Enhancements

Phase 2 (Planned):
- Real-time streaming support
- SQL query generation from natural language
- Advanced microstructure analysis
- Machine learning anomaly detection
- Interactive web dashboard
- Cloud deployment (AWS/GCP)

---

## Getting Started

```bash
# Clone repository
git clone https://github.com/rosalynchan/trading-data-agent.git
cd trading-data-agent

# Setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run with sample data
python -m src.main sample

# Run tests
pytest tests/ -v
```

---

## Author

Rosalyn Chen  
3+ years Quant Tools Developer at tier-1 investment bank  
GitHub: @rosalynchan  
Email: xiaoqingwala@gmail.com

---

## Status

**Current**: Core architecture and foundational agents (In Progress)  
**Timeline**: 8 weeks for full implementation  
**Commitment**: Built in spare time as personal learning project
# Project 1: Trading Data Multi-Agent Assistant

## Project Overview

**Purpose**: Automate trading data ingestion, quality assurance, microstructure analysis, and report generation using multi-agent AI system.

**Inspired by**: Real workflow challenges at tier-1 investment banks where traders spend hours on manual data quality checks.

**Personal Project**: Built independently in spare time. Not using any proprietary company code.

---

## Key Requirements

### Functional Requirements

#### 1. Data Ingestion
- Load trading tick data from multiple sources (CSV, Parquet, Excel)
- Support automatic data type detection
- Extract metadata (row count, columns, data types)
- Handle missing files gracefully

#### 2. Data Quality & Cleaning
- Detect and remove missing values
- Identify and eliminate duplicate records
- Detect data type inconsistencies
- Flag anomalies (negative prices, zero quantities, etc.)
- Generate quality metrics report

#### 3. Data Analysis
- Calculate microstructure features (VWAP, OHLC, imbalance, depth)
- Perform tick replay simulation
- Generate statistical summaries
- Detect price jumps and unusual patterns

#### 4. Reporting
- Generate HTML reports with visualizations
- Include data summary statistics
- Display quality metrics
- Create searchable data previews
- Export to multiple formats

### Technical Requirements

- **Multi-Agent Architecture**: Separate agents for different tasks
- **Error Handling**: Graceful error handling and logging
- **Testing**: Unit tests for each component
- **Documentation**: Clear code documentation and usage examples
- **Extensibility**: Easy to add new agents and features

---

## System Architecture

```
User Input (data source)
    ↓
┌─────────────────────────────┐
│   TradingDataAssistant      │ (Main Orchestrator)
│   Coordinates all agents    │
└─────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────┐
│             Multi-Agent Pipeline                 │
├─────────────────────────────────────────────────┤
│ IngestionAgent     → Loads data from files      │
│ CleaningAgent      → Handles quality checks     │
│ AnalysisAgent      → Calculates metrics         │
│ ReportingAgent     → Generates HTML reports     │
└─────────────────────────────────────────────────┘
    ↓
  Output: Clean data + Quality report + HTML report
```

---

## Project Structure

```
trading-data-agent/
├── src/
│   ├── agents/              # Agent implementations
│   │   ├── base_agent.py
│   │   ├── ingestion_agent.py
│   │   ├── cleaning_agent.py
│   │   ├── analysis_agent.py
│   │   ├── reporting_agent.py
│   │   └── planner_agent.py
│   ├── tools/               # Utility functions
│   │   ├── data_loader.py
│   │   ├── validators.py
│   │   └── anomaly_detector.py
│   ├── utils/               # Configuration and logging
│   │   ├── logger.py
│   │   └── config.py
│   └── main.py              # Entry point
├── tests/
│   ├── test_agents.py
│   ├── test_tools.py
│   └── fixtures/
├── docs/
│   ├── architecture.md
│   ├── api_reference.md
│   └── design_decisions.md
├── examples/
│   ├── basic_usage.py
│   └── sample_data/
├── README.md
├── requirements.txt
├── setup.py
├── .env.example
├── .gitignore
└── LICENSE
```

---

## Agent Responsibilities

### BaseAgent (Abstract Class)
- **Purpose**: Define common interface for all agents
- **Key Methods**:
  - `__init__(name, description)` - Initialize agent
  - `process(input_data)` - Core processing logic
  - `validate_input(data)` - Input validation

### IngestionAgent
- **Input**: File path (CSV, Parquet, Excel)
- **Output**: Pandas DataFrame + metadata
- **Tasks**:
  - Detect file format automatically
  - Read data into memory
  - Extract schema information
  - Return row/column counts

### CleaningAgent
- **Input**: Raw DataFrame
- **Output**: Clean DataFrame + quality report
- **Tasks**:
  - Handle missing values
  - Remove duplicate rows
  - Fix data types
  - Detect anomalies (negative prices, zero quantities, etc.)

### AnalysisAgent
- **Input**: Clean DataFrame
- **Output**: Analysis results with metrics
- **Tasks**:
  - Calculate VWAP, OHLC, spreads
  - Detect price jumps
  - Compute order book imbalance
  - Generate statistical summaries

### ReportingAgent
- **Input**: Analyzed data + quality metrics
- **Output**: HTML report file
- **Tasks**:
  - Create professional HTML report
  - Include data preview tables
  - Display charts and visualizations
  - Embed quality metrics

### PlannerAgent
- **Purpose**: Orchestrate workflow
- **Tasks**:
  - Determine processing steps needed
  - Define agent execution order
  - Handle conditional routing

---

## Data Flow Example

```
Input: "trading_ticks.csv"
    ↓
IngestionAgent
  - Loads 10,000 rows × 8 columns
  - Detects columns: timestamp, symbol, price, quantity, bid, ask, bid_size, ask_size
    ↓
CleaningAgent
  - Removes 50 rows with missing values
  - Removes 30 duplicate rows
  - Detects 5 negative prices (anomalies)
  - Final: 9,920 clean rows
    ↓
AnalysisAgent
  - Calculates VWAP: $150.45
  - Detects 3 price jumps > 0.5%
  - Computes bid-ask spread statistics
    ↓
ReportingAgent
  - Generates: report_20240101_093000.html
  - Includes: summary, quality metrics, data preview, charts
    ↓
Output: Clean data + HTML report
```

---

## Technology Stack

| Component | Technology |
|-----------|------------|
| Data Processing | Pandas, NumPy |
| Agent Framework | LangChain, Custom classes |
| Configuration | Pydantic, Python-dotenv |
| Logging | Loguru |
| Testing | Pytest |
| Web Framework | FastAPI (future) |
| Reports | Jinja2 templates, HTML/CSS |

---

## Success Metrics

- [x] Multi-agent system with clear separation of concerns
- [x] Handle multiple data formats (CSV, Parquet, Excel)
- [x] Detect and report data quality issues
- [x] Generate professional HTML reports
- [x] Comprehensive error handling and logging
- [x] Full test coverage for core components
- [x] Clear documentation and examples

---

## Future Enhancements

Phase 2 (Planned):
- Real-time streaming support
- SQL query generation from natural language
- Advanced microstructure analysis
- Machine learning anomaly detection
- Interactive web dashboard
- Cloud deployment (AWS/GCP)

---

## Getting Started

```bash
# Clone repository
git clone https://github.com/rosalynchan/trading-data-agent.git
cd trading-data-agent

# Setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run with sample data
python -m src.main sample

# Run tests
pytest tests/ -v
```
---

## Author

Rosalyn Chen  
3+ years Quant Tools Developer at tier-1 investment bank  
GitHub: @rosalynchan  
Email: xiaoqingwala@gmail.com

---

## Status

**Current**: Core architecture and foundational agents (In Progress)  
**Timeline**: 8 weeks for full implementation  
**Commitment**: Built in spare time as personal learning project