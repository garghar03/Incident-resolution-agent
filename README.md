# AI Incident Resolution Assistant

AI-powered incident resolution assistant that analyzes logs, retrieves runbooks, and generates probable root cause reports using agent orchestration with optional LangGraph workflows.

## Overview

MVP 1 is a log and runbook based root cause assistant. It accepts an `IncidentAlert`, analyzes log signals, retrieves relevant runbook guidance, and returns a structured `IncidentReport` with evidence, confidence, recommended actions, cautions, and missing signals.

## MVP 1 Flow

```text
IncidentAlert
  -> Log Analyzer
  -> Log Insight Agent
  -> Runbook Retrieval Agent
  -> Root Cause Agent
  -> IncidentReport
```

## Project Structure

```text
src/incident_resolution_agent/
  agents/
    log_insight_agent.py
    root_cause_agent.py
  analyzers/
    log_analyzer.py
    file_log_analyzer.py
    loki_log_analyzer.py
    splunk_log_analyzer.py
  models/
    incident.py
    incident_workflow_state.py
    log.py
    report.py
    runbook_models.py
  rag/
    ingestion/
      build_runbook_index.py
    retrieval/
      runbook_retriever.py
      runbook_retrieval_agent.py
  incident_orchestrator.py
  langgraph_incident_orchestrator.py
tests/
data/runbooks/
```

## Design Principles

- Keep the orchestrator thin.
- Keep log parsing, runbook retrieval, and root cause generation inside their own components.
- Return structured outputs from every major step.
- Prefer fallback reports over hard workflow crashes.
- Use the same agents and models for class-based and LangGraph orchestration.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install pytest
```

On Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install pytest
```

## Run MVP 1

Run the simple class-based orchestrator:

```bash
python tests/run_incident_analysis_without_langgraph.py
```

Run the LangGraph orchestrator:

```bash
python tests/run_incident_analysis_langgraph.py
```

Run the lightweight app demo:

```bash
PYTHONPATH=src python -m incident_resolution_agent.app
```

## Run Tests

With pytest:

```bash
PYTHONPATH=src:. pytest -q
```

Without pytest:

```bash
PYTHONPATH=src:. python -m unittest discover -s tests -p "test_*.py"
```

The main MVP 1 end-to-end test is:

```text
IncidentAlert -> IncidentReport
```

It verifies that the orchestrator validates the alert, calls log analysis, generates log insight, retrieves runbook guidance, and returns a final incident report. It also verifies fallback behavior for invalid alerts.

## Add Runbooks

Add markdown runbooks under:

```text
data/runbooks/
```

For best retrieval results, include:

- Clear title
- Issue category, such as `DATABASE`, `KAFKA`, or `DOWNSTREAM_SERVICE`
- Symptoms
- Diagnosis steps
- Recommended actions
- Cautions

Example:

```text
data/runbooks/db_connection_pool_exhaustion.md
```

## Pass an Incident Alert

Create an `IncidentAlert` and pass it to the orchestrator:

```python
from datetime import datetime

from incident_resolution_agent.incident_orchestrator import IncidentOrchestrator
from incident_resolution_agent.models.incident import IncidentAlert

alert = IncidentAlert(
    incident_id="INC-1001",
    service_name="payment-service",
    severity="HIGH",
    description="Payment failures increased suddenly",
    start_time=datetime.fromisoformat("2026-06-10T10:15:00"),
    end_time=datetime.fromisoformat("2026-06-10T10:45:00"),
)

report = orchestrator.handle_incident(alert)
```

## Switch Orchestrators

Use the simple orchestrator for MVP debugging:

```python
from incident_resolution_agent.incident_orchestrator import IncidentOrchestrator
```

Use the LangGraph orchestrator when you want the graph-based workflow:

```python
from incident_resolution_agent.langgraph_incident_orchestrator import LangGraphIncidentOrchestrator
```

Both orchestrators follow the same MVP 1 flow and use the same model and agent interfaces.

## MVP 2 Direction

MVP 2 will expand the assistant from log-only investigation to multi-signal incident investigation:

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

Recommended first MVP 2 component: metrics models and metrics analyzer.
