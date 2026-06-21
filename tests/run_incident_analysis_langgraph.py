from datetime import datetime

from incident_resolution_agent.models.incident import IncidentAlert
try:
    from tests.mock_components import (
        MockLogAnalyzer,
        MockLogInsightAgent,
        MockRootCauseAgent,
        MockRunbookRetrievalAgent,
    )
except ModuleNotFoundError:
    from mock_components import (
        MockLogAnalyzer,
        MockLogInsightAgent,
        MockRootCauseAgent,
        MockRunbookRetrievalAgent,
    )


def build_alert() -> IncidentAlert:
    return IncidentAlert(
        incident_id="INC-1001",
        service_name="payment-service",
        severity="HIGH",
        description="Payment failures increased suddenly",
        start_time=datetime.fromisoformat("2026-06-10T10:15:00"),
        end_time=datetime.fromisoformat("2026-06-10T10:45:00"),
    )


def print_report(report, title: str) -> None:
    print(title)
    print("=" * 80)
    print(f"Incident ID: {report.incident_id}")
    print(f"Service: {report.service_name}")
    print(f"Severity: {report.severity}")
    print(f"Issue Category: {report.issue_category}")
    print(f"Confidence: {report.confidence}")
    print(f"Probable Root Cause: {report.probable_root_cause}")
    print(f"Fallback Used: {report.fallback_used}")
    print("\nEvidence:")
    for item in report.evidence:
        print(f"- {item}")
    print("\nRecommended Actions:")
    for item in report.recommended_actions:
        print(f"- {item}")
    print("\nCautions:")
    for item in report.cautions:
        print(f"- {item}")
    print("\nMissing Signals:")
    for item in report.missing_signals:
        print(f"- {item}")
    print("\nHuman Summary:")
    print(report.human_summary)

from incident_resolution_agent.langgraph_incident_orchestrator import LangGraphIncidentOrchestrator


def main() -> None:
    orchestrator = LangGraphIncidentOrchestrator(
        log_analyzer=MockLogAnalyzer(),
        log_insight_agent=MockLogInsightAgent(),
        runbook_retrieval_agent=MockRunbookRetrievalAgent(),
        root_cause_agent=MockRootCauseAgent(),
    )
    report = orchestrator.handle_incident(build_alert())
    print_report(report, "LangGraph Incident Report")


if __name__ == "__main__":
    main()
