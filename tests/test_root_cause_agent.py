from datetime import datetime
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(1, str(PROJECT_ROOT))


from incident_resolution_agent.agents.root_cause_agent import RootCauseAgent
from incident_resolution_agent.models.incident import IncidentAlert
from incident_resolution_agent.models.log import GroupedError, LogAnalysisResult, LogInsightResult
from incident_resolution_agent.models.metric import (
    MetricAnalysisResult,
    MetricSignal,
    MetricsInsightResult,
)
from incident_resolution_agent.models.runbook_models import RunbookResult


def build_alert() -> IncidentAlert:
    return IncidentAlert(
        incident_id="INC-1001",
        service_name="payment-service",
        severity="HIGH",
        description="Payment failures increased suddenly",
        start_time=datetime.fromisoformat("2026-06-10T10:15:00"),
        end_time=datetime.fromisoformat("2026-06-10T10:45:00"),
    )


def build_log_analysis_result() -> LogAnalysisResult:
    return LogAnalysisResult(
        service_name="payment-service",
        total_logs=5000,
        error_count=342,
        warning_count=120,
        top_errors=[
            GroupedError(
                message_pattern="HikariPool connection timeout",
                count=188,
                first_seen=datetime.fromisoformat("2026-06-10T10:20:01"),
                last_seen=datetime.fromisoformat("2026-06-10T10:44:12"),
            ),
            GroupedError(
                message_pattern="SQLTransientConnectionException",
                count=97,
                first_seen=datetime.fromisoformat("2026-06-10T10:20:05"),
                last_seen=datetime.fromisoformat("2026-06-10T10:43:50"),
            ),
        ],
        evidence=[
            "ERROR HikariPool-1 - Connection is not available, request timed out after 30000ms",
            "ERROR SQLTransientConnectionException: Connection is not available",
        ],
        trace_ids=["abc-101", "abc-102"],
    )


def build_log_insight_result() -> LogInsightResult:
    return LogInsightResult(
        suspected_issue="Possible DB connection pool exhaustion",
        issue_category="DATABASE",
        confidence=0.87,
        reasoning=(
            "Most high-frequency errors are related to Hikari connection acquisition "
            "timeouts and SQL transient connection failures."
        ),
        next_checks=[
            "Check Hikari active and idle connection metrics.",
            "Check database max connection usage.",
            "Check slow queries during the incident window.",
            "Check recent connection pool configuration changes.",
        ],
        recommended_runbook_query="DB connection pool exhaustion Hikari SQLTransientConnectionException",
        recommended_next_agents=["runbook_retrieval_agent"],
        fallback_used=False,
    )


def build_runbook_result() -> RunbookResult:
    return RunbookResult(
        matched_runbooks=["DB Connection Pool Exhaustion Runbook"],
        confidence=0.90,
        relevant_steps=[
            "Check Hikari active connection count.",
            "Check Hikari idle connection count.",
            "Check database max connection usage.",
            "Check slow query logs during the incident window.",
            "Consider rollback only if a recent configuration or deployment change is confirmed.",
        ],
        cautions=[
            "Do not blindly increase pool size without checking database max connections.",
            "Do not restart all pods at once.",
        ],
        source_documents=["db_connection_pool_exhaustion.md"],
        retrieved_chunks=["db_connection_pool_exhaustion.md::chunk-0"],
        summary=(
            "The matched runbook recommends checking database connection pool saturation, "
            "database max connections, and slow queries before remediation."
        ),
        fallback_used=False,
    )


def build_metric_analysis_result() -> MetricAnalysisResult:
    alert = build_alert()

    return MetricAnalysisResult(
        service_name=alert.service_name,
        baseline_window_start=datetime.fromisoformat("2026-06-10T09:45:00"),
        baseline_window_end=datetime.fromisoformat("2026-06-10T10:15:00"),
        analyzed_window_start=alert.start_time,
        analyzed_window_end=alert.end_time,
        total_metrics=3,
        signals=[
            MetricSignal(
                metric_name="db.connection.pool.active",
                signal_type="DB_POOL_ACTIVE_HIGH",
                severity="WARN",
                summary="DB pool active connections were high during the incident window.",
                baseline_value=30.0,
                incident_value=94.0,
                change_percent=213.33,
                evidence=["DB pool active connections increased from 30 to 94."],
            ),
            MetricSignal(
                metric_name="db.connection.pool.pending",
                signal_type="DB_POOL_PENDING",
                severity="WARN",
                summary="DB pool pending connections increased during the incident window.",
                baseline_value=0.0,
                incident_value=16.0,
                change_percent=None,
                evidence=["DB pool pending connections increased from 0 to 16."],
            ),
        ],
        evidence=[
            "DB pool active connections increased from 30 to 94.",
            "DB pool pending connections increased from 0 to 16.",
        ],
        missing_metrics=[],
        fallback_used=False,
    )


def build_metrics_insight_result() -> MetricsInsightResult:
    return MetricsInsightResult(
        suspected_issue="Possible database connection pool saturation",
        issue_category="DATABASE",
        confidence=0.88,
        reasoning=(
            "DB active connection usage was high and pending connections were detected "
            "during the incident window."
        ),
        supporting_signals=[
            "DB pool active connections were high during the incident window.",
            "DB pool pending connections increased during the incident window.",
        ],
        next_checks=[
            "Check database max connection usage.",
            "Check Hikari active and pending connection metrics.",
            "Check slow queries during the incident window.",
        ],
        recommended_runbook_query=(
            "database connection pool saturation pending connections latency spike"
        ),
        fallback_used=False,
    )

def test_root_cause_agent_includes_metrics_evidence():
    agent = RootCauseAgent(llm=None)

    report = agent.generate_report(
        alert=build_alert(),
        log_analysis_result=build_log_analysis_result(),
        log_insight_result=build_log_insight_result(),
        runbook_result=build_runbook_result(),
        metric_analysis_result=build_metric_analysis_result(),
        metrics_insight_result=build_metrics_insight_result(),
    )

    evidence_text = " ".join(report.evidence)
    missing_text = " ".join(report.missing_signals)

    assert "Metrics Insight Agent suspected" in evidence_text
    assert "Metric signal" in evidence_text
    assert "Metrics data was not analyzed" not in missing_text
    assert report.confidence >= 0.90


def test_root_cause_agent_still_works_without_metrics():
    agent = RootCauseAgent(llm=None)

    report = agent.generate_report(
        alert=build_alert(),
        log_analysis_result=build_log_analysis_result(),
        log_insight_result=build_log_insight_result(),
        runbook_result=build_runbook_result(),
    )

    assert report.incident_id == "INC-1001"
    assert report.service_name == "payment-service"
    assert report.fallback_used is True
    assert "Metrics data was not analyzed" in " ".join(report.missing_signals)


def main() -> None:
    agent = RootCauseAgent(llm=None)

    report = agent.generate_report(
        alert=build_alert(),
        log_analysis_result=build_log_analysis_result(),
        log_insight_result=build_log_insight_result(),
        runbook_result=build_runbook_result(),
        metric_analysis_result=build_metric_analysis_result(),
        metrics_insight_result=build_metrics_insight_result(),
    )

    print("Incident Report")
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


if __name__ == "__main__":
    main()   