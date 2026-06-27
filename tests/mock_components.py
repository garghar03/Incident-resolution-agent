from datetime import datetime

from incident_resolution_agent.models.incident import IncidentAlert
from incident_resolution_agent.models.log import GroupedError, LogAnalysisResult, LogInsightResult
from incident_resolution_agent.models.report import IncidentReport
from incident_resolution_agent.models.runbook_models import RunbookResult
from incident_resolution_agent.models.metric import (
    MetricAnalysisResult,
    MetricSignal,
    MetricsInsightResult,
)


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
    def __init__(self):
        self.last_request = None

    def search(self, request) -> RunbookResult:
        self.last_request = request

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
                "The matched runbook recommends checking database connection pool "
                "saturation, database max connections, and slow queries before remediation."
            ),
            fallback_used=False,
        )


class MockRootCauseAgent:
    def __init__(self):
        self.last_metric_analysis_result = None
        self.last_metrics_insight_result = None

    def generate_report(
        self,
        alert,
        log_analysis_result,
        log_insight_result,
        runbook_result,
        metric_analysis_result=None,
        metrics_insight_result=None,
    ) -> IncidentReport:
        self.last_metric_analysis_result = metric_analysis_result
        self.last_metrics_insight_result = metrics_insight_result

        evidence = [
            f"{log_analysis_result.error_count} errors found during the incident window.",
            f"Top error: {log_analysis_result.top_errors[0].message_pattern}",
            f"Matched runbook: {runbook_result.matched_runbooks[0]}",
        ]

        if metrics_insight_result:
            evidence.append(f"Metrics insight: {metrics_insight_result.suspected_issue}")

        return IncidentReport(
            incident_id=alert.incident_id,
            service_name=alert.service_name,
            severity=alert.severity,
            probable_root_cause=log_insight_result.suspected_issue,
            issue_category=log_insight_result.issue_category,
            confidence=0.86,
            evidence=evidence,
            recommended_actions=log_insight_result.next_checks + runbook_result.relevant_steps,
            cautions=runbook_result.cautions,
            missing_signals=[
                "Deployment history was not analyzed in this workflow.",
                "Distributed traces were not analyzed in this workflow.",
            ],
            human_summary="Available evidence suggests database connection pool exhaustion.",
            fallback_used=False,
        )

class MockMetricsAnalyzer:
    def __init__(self):
        self.called = False

    def analyze(self, alert):
        self.called = True

        return MetricAnalysisResult(
            service_name=alert.service_name,
            baseline_window_start=alert.start_time,
            baseline_window_end=alert.start_time,
            analyzed_window_start=alert.start_time,
            analyzed_window_end=alert.end_time,
            total_metrics=3,
            signals=[
                MetricSignal(
                    metric_name="db.connection.pool.active",
                    signal_type="DB_POOL_ACTIVE_HIGH",
                    severity="WARN",
                    summary="DB pool active connections were high.",
                    baseline_value=30.0,
                    incident_value=94.0,
                    change_percent=213.33,
                    evidence=["DB pool active connections increased from 30 to 94."],
                ),
                MetricSignal(
                    metric_name="db.connection.pool.pending",
                    signal_type="DB_POOL_PENDING",
                    severity="WARN",
                    summary="DB pool pending connections were detected.",
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
    
class MockMetricsInsightAgent:
    def __init__(self):
        self.called = False

    def analyze(self, metric_analysis_result):
        self.called = True

        return MetricsInsightResult(
            suspected_issue="Possible database connection pool saturation",
            issue_category="DATABASE",
            confidence=0.88,
            reasoning=(
                "DB active connection usage was high and pending connections "
                "were detected during the incident window."
            ),
            supporting_signals=[
                signal.summary for signal in metric_analysis_result.signals
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