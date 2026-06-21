from datetime import datetime

from incident_resolution_agent.models.incident import IncidentAlert
from incident_resolution_agent.models.log import GroupedError, LogAnalysisResult, LogInsightResult
from incident_resolution_agent.models.report import IncidentReport
from incident_resolution_agent.models.runbook_models import RunbookResult


class MockLogAnalyzer:
    def analyze(self, alert: IncidentAlert) -> LogAnalysisResult:
        return LogAnalysisResult(
            service_name=alert.service_name,
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
            evidence=["ERROR HikariPool-1 - Connection is not available, request timed out after 30000ms"],
            trace_ids=["abc-101", "abc-102"],
        )


class MockLogInsightAgent:
    def analyze(self, log_analysis_result: LogAnalysisResult) -> LogInsightResult:
        return LogInsightResult(
            suspected_issue="Possible DB connection pool exhaustion",
            issue_category="DATABASE",
            confidence=0.87,
            reasoning="Most high-frequency errors are Hikari connection acquisition timeouts and SQL transient connection failures.",
            next_checks=[
                "Check Hikari active and idle connection metrics.",
                "Check database max connection usage.",
                "Check slow queries during the incident window.",
            ],
            recommended_runbook_query="DB connection pool exhaustion Hikari SQLTransientConnectionException",
            recommended_next_agents=["runbook_retrieval_agent"],
            fallback_used=False,
        )


class MockRunbookRetrievalAgent:
    def search(self, request) -> RunbookResult:
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
            summary="The matched runbook recommends checking database connection pool saturation, database max connections, and slow queries before remediation.",
            fallback_used=False,
        )


class MockRootCauseAgent:
    def generate_report(self, alert: IncidentAlert, log_analysis_result: LogAnalysisResult, log_insight_result: LogInsightResult, runbook_result: RunbookResult) -> IncidentReport:
        return IncidentReport(
            incident_id=alert.incident_id,
            service_name=alert.service_name,
            severity=alert.severity,
            probable_root_cause=log_insight_result.suspected_issue,
            issue_category=log_insight_result.issue_category,
            confidence=0.86,
            evidence=[
                f"{log_analysis_result.error_count} errors found during the incident window.",
                f"Top error: {log_analysis_result.top_errors[0].message_pattern}",
                f"Matched runbook: {runbook_result.matched_runbooks[0]}",
            ],
            recommended_actions=log_insight_result.next_checks + runbook_result.relevant_steps,
            cautions=runbook_result.cautions,
            missing_signals=[
                "Metrics data was not analyzed in MVP 1.",
                "Deployment history was not analyzed in MVP 1.",
                "Distributed traces were not analyzed in MVP 1.",
            ],
            human_summary="Available evidence suggests database connection pool exhaustion.",
            fallback_used=False,
        )
