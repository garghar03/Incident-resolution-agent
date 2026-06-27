from datetime import datetime
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(1, str(PROJECT_ROOT))

from incident_resolution_agent.incident_orchestrator import IncidentOrchestrator
from incident_resolution_agent.langgraph_incident_orchestrator import LangGraphIncidentOrchestrator
from incident_resolution_agent.models.incident import IncidentAlert

from tests.mock_components import (
    MockLogAnalyzer,
    MockLogInsightAgent,
    MockMetricsInsightAgent,
    MockMetricsAnalyzer,
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

def test_class_orchestrator_still_works_without_metrics(self):
    orchestrator = IncidentOrchestrator(
        log_analyzer=MockLogAnalyzer(),
        log_insight_agent=MockLogInsightAgent(),
        runbook_retrieval_agent=MockRunbookRetrievalAgent(),
        root_cause_agent=MockRootCauseAgent(),
    )

    report = orchestrator.handle_incident(build_alert())

    self.assertEqual("INC-1001", report.incident_id)
    self.assertEqual("DATABASE", report.issue_category)
    self.assertFalse(report.fallback_used)

def test_class_orchestrator_calls_metrics_components(self):
    metrics_analyzer = MockMetricsAnalyzer()
    metrics_insight_agent = MockMetricsInsightAgent()
    root_cause_agent = MockRootCauseAgent()

    orchestrator = IncidentOrchestrator(
        log_analyzer=MockLogAnalyzer(),
        log_insight_agent=MockLogInsightAgent(),
        metrics_analyzer=metrics_analyzer,
        metrics_insight_agent=metrics_insight_agent,
        runbook_retrieval_agent=MockRunbookRetrievalAgent(),
        root_cause_agent=root_cause_agent,
    )

    report = orchestrator.handle_incident(build_alert())

    self.assertTrue(metrics_analyzer.called)
    self.assertTrue(metrics_insight_agent.called)
    self.assertIsNotNone(root_cause_agent.last_metric_analysis_result)
    self.assertIsNotNone(root_cause_agent.last_metrics_insight_result)
    self.assertFalse(report.fallback_used)

def test_runbook_query_combines_log_and_metric_queries(self):
    runbook_agent = MockRunbookRetrievalAgent()

    orchestrator = IncidentOrchestrator(
        log_analyzer=MockLogAnalyzer(),
        log_insight_agent=MockLogInsightAgent(),
        metrics_analyzer=MockMetricsAnalyzer(),
        metrics_insight_agent=MockMetricsInsightAgent(),
        runbook_retrieval_agent=runbook_agent,
        root_cause_agent=MockRootCauseAgent(),
    )

    orchestrator.handle_incident(build_alert())

    self.assertIsNotNone(runbook_agent.last_request)
    self.assertIn("DB connection pool exhaustion", runbook_agent.last_request.query)
    self.assertIn("database connection pool saturation", runbook_agent.last_request.query)
    self.assertEqual("DATABASE", runbook_agent.last_request.category)
    self.assertEqual(0.88, runbook_agent.last_request.insight_confidence)

def test_langgraph_orchestrator_works_without_metrics(self):
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

def test_langgraph_orchestrator_works_with_metrics(self):
    metrics_analyzer = MockMetricsAnalyzer()
    metrics_insight_agent = MockMetricsInsightAgent()
    root_cause_agent = MockRootCauseAgent()

    orchestrator = LangGraphIncidentOrchestrator(
        log_analyzer=MockLogAnalyzer(),
        log_insight_agent=MockLogInsightAgent(),
        metrics_analyzer=metrics_analyzer,
        metrics_insight_agent=metrics_insight_agent,
        runbook_retrieval_agent=MockRunbookRetrievalAgent(),
        root_cause_agent=root_cause_agent,
    )

    report = orchestrator.handle_incident(build_alert())

    self.assertTrue(metrics_analyzer.called)
    self.assertTrue(metrics_insight_agent.called)
    self.assertIsNotNone(root_cause_agent.last_metric_analysis_result)
    self.assertIsNotNone(root_cause_agent.last_metrics_insight_result)
    self.assertEqual("INC-1001", report.incident_id)
    self.assertFalse(report.fallback_used)

if __name__ == "__main__":
    unittest.main()
