# AI Incident Resolution Assistant

AI-powered incident resolution assistant that analyzes logs, retrieves runbooks, and generates probable root cause reports using agent orchestration with optional LangGraph workflows.

## Overview

This project helps investigate production incidents by combining deterministic analysis, runbook retrieval, and AI-assisted reasoning.

The MVP focuses on log-based incident investigation. It accepts an incident alert, analyzes related logs, retrieves relevant runbooks, and generates a structured root cause report with evidence, confidence, recommended actions, cautions, and missing signals.

## MVP 1 Flow

```text
IncidentAlert
  -> Log Analyzer
  -> Log Insight Agent
  -> Runbook Retrieval Agent
  -> Root Cause Agent
  -> IncidentReport
```

## Key Features

- Analyze incident logs for errors, warnings, trace IDs, and repeated failure patterns
- Generate log insights such as suspected issue category, confidence, reasoning, and next checks
- Retrieve relevant runbook guidance using a search request generated from incident context
- Generate a final incident report with probable root cause, supporting evidence, and recommended actions
- Support both simple class-based orchestration and LangGraph-based orchestration
- Provide fallback reporting when workflow steps fail

## Project Structure

```text
app/
  agents/
    log_insight_agent.py
    runbook_retrieval_agent.py
    root_cause_agent.py

  analyzers/
    log_analyzer.py

  ingestion/
    runbook_ingestion.py

  retrievers/
    runbook_retriever.py

  models/
    incident_models.py
    log_models.py
    runbook_models.py
    report_models.py

  orchestrator/
    incident_workflow_state.py
    incident_orchestrator.py
    langgraph_incident_orchestrator.py

  logs/
  runbooks/

tests/
```

## Core Components

| Component | Responsibility |
|---|---|
| `IncidentAlert` | Input model for incident details |
| `Log Analyzer` | Parses and summarizes logs for the incident window |
| `Log Insight Agent` | Converts log analysis into suspected issue, reasoning, and next checks |
| `Runbook Retriever` | Searches runbook content for relevant remediation guidance |
| `Runbook Retrieval Agent` | Wraps retrieval result into structured runbook guidance |
| `Root Cause Agent` | Produces the final incident report |
| `Incident Orchestrator` | Coordinates the complete workflow |
| `LangGraph Orchestrator` | Graph-based workflow version using LangGraph |

## Orchestration Options

### 1. Class-Based Orchestrator

The simple orchestrator is best for MVP development and debugging.

```text
validate_alert
  -> analyze_logs
  -> generate_log_insight
  -> retrieve_runbook
  -> generate_root_cause_report
```

### 2. LangGraph Orchestrator

The LangGraph version models the same workflow as a state graph.

```text
START
  -> validate_alert
  -> analyze_logs
  -> generate_log_insight
  -> retrieve_runbook
  -> generate_root_cause_report
  -> END
```

If any step fails, the graph routes to:

```text
build_failure_report -> END
```

## Data Models

### IncidentAlert

Represents the incident input.

```text
incident_id
service_name
severity
description
start_time
end_time
```

### IncidentReport

Represents the final investigation output.

```text
incident_id
service_name
severity
probable_root_cause
issue_category
confidence
evidence
recommended_actions
cautions
missing_signals
human_summary
fallback_used
```

## Example Output

```text
Incident ID: INC-1001
Service: payment-service
Severity: HIGH
Issue Category: DATABASE
Confidence: 0.86

Probable Root Cause:
Possible DB connection pool exhaustion

Evidence:
- High number of Hikari connection timeout errors
- SQL transient connection exceptions detected
- Relevant DB connection pool runbook matched

Recommended Actions:
- Check database max connection usage
- Check Hikari active and idle connection metrics
- Review slow queries during the incident window
- Validate whether a recent deployment changed DB connection behavior
```

## Installation

Create and activate a virtual environment:

```bash
python -m venv .venv
```

On Windows:

```bash
.venv\Scripts\activate
```

On macOS/Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

If using LangGraph:

```bash
pip install langgraph
```

## Running the Project

Run the class-based orchestrator:

```bash
python run_incident_analysis_without_langgraph.py
```

Run the LangGraph orchestrator:

```bash
python run_incident_analysis_langgraph.py
```

## Testing

Run tests with:

```bash
pytest
```

Recommended MVP 1 test:

```text
IncidentAlert -> IncidentReport
```

The test should verify that:

- The alert is validated
- Logs are analyzed
- Log insight is generated
- Runbook guidance is retrieved
- Root cause report is generated
- Failure paths return a fallback report

## MVP 1 Status

MVP 1 focuses on:

- Log analysis
- Runbook retrieval
- Root cause report generation
- Simple orchestration
- Optional LangGraph orchestration

## MVP 2 Roadmap

MVP 2 will expand the assistant from log-only investigation to multi-signal incident investigation.

Planned additions:

- Metrics Agent
- Deployment Change Agent
- Trace or Dependency Agent
- Incident Timeline
- Confidence Scoring v2
- Conditional LangGraph routing

Target MVP 2 flow:

```text
IncidentAlert
  -> Log Analyzer
  -> Log Insight Agent
  -> Metrics Agent
  -> Deployment Change Agent
  -> Trace/Dependency Agent
  -> Runbook Retrieval Agent
  -> Root Cause Agent v2
  -> IncidentReport v2
```

## Design Principles

- Keep the orchestrator thin
- Keep agents independently testable
- Avoid mixing workflow logic with analysis logic
- Return structured outputs from every step
- Prefer fallback reports over hard crashes
- Make the workflow easy to migrate from simple orchestration to LangGraph

## Repository Description

```text
AI-powered incident resolution assistant that analyzes logs, retrieves runbooks, and generates probable root cause reports using agent orchestration with optional LangGraph workflows.
```
