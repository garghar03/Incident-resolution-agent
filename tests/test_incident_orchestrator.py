from datetime import datetime
import unittest

from incident_resolution_agent.incident_orchestrator import IncidentOrchestrator
from incident_resolution_agent.langgraph_incident_orchestrator import LangGraphIncidentOrchestrator
from incident_resolution_agent.models.incident import IncidentAlert

from tests.mock_components import (
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


def build_class_orchestrator() -> IncidentOrchestrator:
    return IncidentOrchestrator(
        log_analyzer=MockLogAnalyzer(),
        log_insight_agent=MockLogInsightAgent(),
        runbook_retrieval_agent=MockRunbookRetrievalAgent(),
        root_cause_agent=MockRootCauseAgent(),
    )


class IncidentOrchestratorTest(unittest.TestCase):
    def test_class_orchestrator_returns_incident_report(self) -> None:
        report = build_class_orchestrator().handle_incident(build_alert())

        self.assertEqual("INC-1001", report.incident_id)
        self.assertEqual("payment-service", report.service_name)
        self.assertEqual("HIGH", report.severity)
        self.assertEqual("DATABASE", report.issue_category)
        self.assertFalse(report.fallback_used)
        self.assertGreater(report.confidence, 0.0)
        self.assertIn("Possible DB connection pool exhaustion", report.probable_root_cause)
        self.assertTrue(report.evidence)
        self.assertTrue(report.recommended_actions)

    def test_class_orchestrator_returns_failure_report_for_invalid_alert(self) -> None:
        alert = build_alert()
        alert.incident_id = ""

        report = build_class_orchestrator().handle_incident(alert)

        self.assertTrue(report.fallback_used)
        self.assertEqual("UNKNOWN", report.issue_category)
        self.assertIn("incident_id is required", " ".join(report.evidence))

    def test_langgraph_orchestrator_returns_incident_report(self) -> None:
        orchestrator = LangGraphIncidentOrchestrator(
            log_analyzer=MockLogAnalyzer(),
            log_insight_agent=MockLogInsightAgent(),
            runbook_retrieval_agent=MockRunbookRetrievalAgent(),
            root_cause_agent=MockRootCauseAgent(),
        )

        report = orchestrator.handle_incident(build_alert())

        self.assertEqual("INC-1001", report.incident_id)
        self.assertEqual("DATABASE", report.issue_category)
        self.assertFalse(report.fallback_used)


if __name__ == "__main__":
    unittest.main()
