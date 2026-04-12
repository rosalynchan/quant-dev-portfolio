# Trading Data Multi-Agent Assistant - System Design

## Status

🟡 **Design Phase** This document specifies the system architecture and design. 
Implementation of agents has not started yet.

---

## Overview

### Problem
Trading teams spend hours on repetitive data tasks:
- Loading data from multiple sources
- Validating data quality  
- Removing duplicates and handling missing values
- Detecting anomalies
- Generating quality reports

### Solution
A multi-agent system where each agent handles one specific task, all coordinated by an orchestrator.

---

## System Architecture

```
User Input (data file path)
    ↓
┌───────────────────────────┐
│ TradingDataAssistant      │ (Main Orchestrator)
│ - Coordinates all agents  │
│ - Manages data flow       │
│ - Handles errors          │
└───────────────────────────┘
    ↓
┌──────────────────────────────────────────────┐
│         Multi-Agent Pipeline                  │
├──────────────────────────────────────────────┤
│                                              │
│  IngestionAgent                              │
│  Input: file path                            │
│  Output: DataFrame + metadata                │
│                    ↓                          │
│  CleaningAgent                               │
│  Input: raw DataFrame                        │
│  Output: clean DataFrame + quality report    │
│                    ↓                          │
│  AnalysisAgent                               │
│  Input: clean DataFrame                      │
│  Output: calculated metrics                  │
│                    ↓                          │
│  ReportingAgent                              │
│  Input: analyzed data + metrics              │
│  Output: HTML report file                    │
│                                              │
└──────────────────────────────────────────────┘
    ↓
Output: Clean data + Quality report + HTML report
```

---

## Agent Responsibilities

### 1. IngestionAgent
**Loads data from files**

| Aspect | Detail |
|--------|--------|
| Input | File path (string) |
| Output | DataFrame, rows, columns, data types |
| Supported Formats | CSV, Parquet, Excel |
| Error Handling | File not found, unsupported format, read errors |
| Responsibility | Detect file format and load correctly |

### 2. CleaningAgent  
**Cleans and validates data quality**

| Aspect | Detail |
|--------|--------|
| Input | Raw DataFrame |
| Output | Clean DataFrame, quality report |
| Tasks | Remove missing values, eliminate duplicates, detect anomalies |
| Anomalies | Negative prices, zero quantities, suspicious values |
| Report | Rows removed, removal rate, anomalies found |
| Error Handling | Invalid DataFrame, empty data |

### 3. AnalysisAgent
**Calculates trading metrics**

| Aspect | Detail |
|--------|--------|
| Input | Clean DataFrame |
| Output | Metrics dictionary |
| Calculations | Mean, min, max, std dev for prices and volumes |
| Report | Summary statistics by column |
| Error Handling | Missing columns, non-numeric data |

### 4. ReportingAgent
**Generates HTML reports**

| Aspect | Detail |
|--------|--------|
| Input | Clean data, quality metrics |
| Output | HTML file path |
| Report Contents | Summary, quality metrics, data preview, column info |
| Format | Professional HTML with tables |
| File Location | `./outputs/report_[timestamp].html` |
| Error Handling | Write errors, missing columns |

### 5. PlannerAgent
**Plans the workflow**

| Aspect | Detail |
|--------|--------|
| Input | Task request |
| Output | List of workflow steps |
| Purpose | Define the sequence of agent execution |
| Currently | Returns fixed workflow: ingest → clean → analyze → report |

---

## Data Flow Example

```
Input: "trading_ticks.csv" (1000 rows)
    ↓
IngestionAgent loads CSV
  → 1000 rows, 8 columns (timestamp, symbol, price, qty, bid, ask, bid_size, ask_size)
    ↓
CleaningAgent cleans data
  → Removes 50 rows with missing values
  → Removes 30 duplicate rows  
  → Detects 5 negative prices (anomaly)
  → Output: 920 clean rows + quality report
    ↓
AnalysisAgent calculates metrics
  → Price mean: $150.25
  → Price std dev: $2.10
  → Total volume: 920,000 units
  → Volume mean: 1,000 per row
    ↓
ReportingAgent generates report
  → Creates: report_20260115_093000.html
  → Includes: Summary, quality metrics, data preview
    ↓
Output to user:
  - Clean CSV file: 920 rows
  - Quality report: 80 rows removed (8% loss)
  - HTML report: report_20260115_093000.html
```

---

## Agent Interface (Contract)

All agents implement the same interface:

```python
class Agent:
    # Attributes
    name: str              # Agent identifier
    description: str       # What this agent does
    
    # Methods
    process(input_data: Dict) -> Dict
        # Input: Dictionary with agent-specific data
        # Output: {
        #     "status": "success" or "failed",
        #     "data": processed_data (if success),
        #     "error": error_message (if failed)
        # }
    
    validate_input(input_data: Dict) -> bool
        # Returns: True if input is valid, False otherwise
```

### Response Format

**Success:**
```python
{
    "status": "success",
    "data": result_data,
    "additional_field": additional_value
}
```

**Failure:**
```python
{
    "status": "failed",
    "error": "Detailed error message"
}
```

---

## Processing Pipeline

### Step-by-step execution

```
Step 1: Load data
  Agent: IngestionAgent
  Input: {"source": "data.csv"}
  Check: Did it load successfully?
  
Step 2: Clean data
  Agent: CleaningAgent
  Input: {"data": DataFrame}
  Check: Did cleaning complete?
  
Step 3: Analyze
  Agent: AnalysisAgent
  Input: {"data": cleaned_DataFrame}
  Check: Were metrics calculated?
  
Step 4: Report
  Agent: ReportingAgent
  Input: {"data": clean_data, "quality_report": metrics}
  Check: Was report generated?
  
Step 5: Return results
  Return: All results and status
```

---

## Error Handling Strategy

### Each agent:
1. Validates its own input before processing
2. Logs what it's doing at each step
3. Catches any exceptions that occur
4. Returns `{"status": "failed", "error": message}` on error
5. Returns `{"status": "success", ...}` on success

### The orchestrator:
1. Checks status of each agent call
2. Stops pipeline if any agent fails
3. Returns the failure to the user
4. Never raises exceptions - always returns error dict

---

## Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Data Processing | Pandas | Read/write DataFrames |
| Agent Framework | Custom Python classes | Simple, explicit design |
| Configuration | Pydantic | Type-safe settings |
| Logging | Loguru | Better than standard logging |
| Testing | Pytest | Unit tests for each agent |
| Reports | Jinja2, HTML/CSS | Generate HTML reports |
| Utilities | NumPy | Array calculations |

---

## Key Design Principles

1. **Each agent does one thing**
   - IngestionAgent only loads data
   - CleaningAgent only cleans data
   - Etc.

2. **Consistent error handling**
   - All agents return same format
   - No exceptions propagate
   - All errors are logged

3. **Explicit data flow**
   - Clear what each step does
   - Easy to debug
   - Easy to test

4. **Extensible design**
   - Add new agents without changing existing ones
   - New tools can be created independently
   - Plugin agents using BaseAgent interface

5. **Testable architecture**
   - Each agent can be tested in isolation
   - Mock inputs for testing
   - No hidden dependencies

---

## Future Enhancements

**Phase 2:**
- Real-time streaming data support
- SQL query generation from natural language
- Machine learning-based anomaly detection
- Interactive web dashboard
- RESTful API endpoints

**Phase 3:**
- Cloud deployment (AWS/GCP)
- Distributed processing
- Advanced microstructure analysis
- Performance optimization

---

## Project Structure

Files will be created incrementally as implementation progresses:

```
src/
├── agents/           # Agent implementations (created during development)
├── tools/            # Utility functions (created as needed)
├── utils/            # Logging and configuration
└── main.py           # Main orchestrator

tests/                # Tests (created as agents are implemented)
docs/                 # Documentation (architecture.md, etc.)
examples/             # Usage examples and sample data
```

**Implementation approach**: Start with BaseAgent, then add agents one by one. Each agent gets its own file and test file as it's implemented.

---

**This is the complete system design. Implementation follows this specification.**