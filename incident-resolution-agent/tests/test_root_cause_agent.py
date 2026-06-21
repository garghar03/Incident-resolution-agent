from datetime import datetime

from incident_resolution_agent.agents.root_cause_agent import RootCauseAgent
from incident_resolution_agent.models.incident import IncidentAlert
from incident_resolution_agent.models.log import GroupedError, LogAnalysisResult, LogInsightResult
from incident_resolution_agent.models.runbook_models import RunbookResult


def main() -> None:
    alert = IncidentAlert(
        incident_id="INC-1001",
        service_name="payment-service",
        severity="HIGH",
        description="Payment failures increased suddenly",
        start_time=datetime.fromisoformat("2026-06-10T10:15:00"),
        end_time=datetime.fromisoformat("2026-06-10T10:45:00"),
    )

    log_analysis_result = LogAnalysisResult(
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

    log_insight_result = LogInsightResult(
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

    runbook_result = RunbookResult(
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

    agent = RootCauseAgent(llm=None)
    report = agent.generate_report(
        alert=alert,
        log_analysis_result=log_analysis_result,
        log_insight_result=log_insight_result,
        runbook_result=runbook_result,
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
