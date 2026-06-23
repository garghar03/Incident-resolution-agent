from incident_resolution_agent.models.metric import (
    MetricAnalysisResult,
    MetricsInsightResult,
)

class MetricsInsightAgent:
    def analyze(self, metric_analysis_result: MetricAnalysisResult) -> MetricsInsightResult:
        signal_types = {
            signal.signal_type
            for signal in metric_analysis_result.signals
        }

        supporting_signals = [
            signal.summary
            for signal in metric_analysis_result.signals
        ]

        if {"DB_POOL_ACTIVE_HIGH", "DB_POOL_PENDING"}.issubset(signal_types):
            return MetricsInsightResult(
                suspected_issue="Possible database connection pool saturation",
                issue_category="DATABASE",
                confidence=0.85,
                reasoning=(
                    "Database active connection usage was high and pending connections "
                    "were detected during the incident window."
                ),
                supporting_signals=supporting_signals,
                next_checks=[
                    "Check database max connection usage.",
                    "Check Hikari active, idle, and pending connection metrics.",
                    "Check slow query logs during the incident window.",
                    "Check recent connection pool configuration changes.",
                ],
                recommended_runbook_query=(
                    "database connection pool saturation pending connections latency spike"
                ),
                fallback_used=False,
            )

        if {"DB_POOL_PENDING", "LATENCY_SPIKE"}.issubset(signal_types):
            return MetricsInsightResult(
                suspected_issue="Possible database connection wait or backpressure",
                issue_category="DATABASE",
                confidence=0.75,
                reasoning=(
                    "Pending database connections and latency spike were detected together."
                ),
                supporting_signals=supporting_signals,
                next_checks=[
                    "Check database connection wait time.",
                    "Check database max connections.",
                    "Check slow queries and lock waits.",
                ],
                recommended_runbook_query="database connection wait latency spike",
                fallback_used=False,
            )

        if {"CPU_SATURATION", "LATENCY_SPIKE"}.issubset(signal_types):
            return MetricsInsightResult(
                suspected_issue="Possible CPU saturation causing service latency",
                issue_category="KUBERNETES",
                confidence=0.75,
                reasoning=(
                    "CPU usage crossed the saturation threshold while latency increased."
                ),
                supporting_signals=supporting_signals,
                next_checks=[
                    "Check pod CPU usage and throttling.",
                    "Check HPA scaling events.",
                    "Check request volume during the incident.",
                    "Check recent CPU limit changes.",
                ],
                recommended_runbook_query="cpu saturation latency pod throttling",
                fallback_used=False,
            )

        if {"MEMORY_PRESSURE", "LATENCY_SPIKE"}.issubset(signal_types):
            return MetricsInsightResult(
                suspected_issue="Possible memory pressure or garbage collection issue",
                issue_category="MEMORY",
                confidence=0.75,
                reasoning=(
                    "Memory pressure was detected together with increased latency."
                ),
                supporting_signals=supporting_signals,
                next_checks=[
                    "Check heap usage.",
                    "Check GC pause time.",
                    "Check pod memory limits.",
                    "Check OOM kill or restart events.",
                ],
                recommended_runbook_query="memory pressure gc pause latency",
                fallback_used=False,
            )

        if {"TRAFFIC_SPIKE", "ERROR_RATE_SPIKE"}.issubset(signal_types):
            return MetricsInsightResult(
                suspected_issue="Possible traffic surge causing elevated failures",
                issue_category="RATE_LIMITING",
                confidence=0.70,
                reasoning=(
                    "Traffic increased significantly and error rate also increased."
                ),
                supporting_signals=supporting_signals,
                next_checks=[
                    "Check request volume by endpoint.",
                    "Check rate limiting or throttling metrics.",
                    "Check autoscaling behavior.",
                    "Check downstream dependency capacity.",
                ],
                recommended_runbook_query="traffic spike error rate rate limiting autoscaling",
                fallback_used=False,
            )

        if {"ERROR_RATE_SPIKE", "LATENCY_SPIKE"}.issubset(signal_types):
            return MetricsInsightResult(
                suspected_issue="Service degradation detected from metrics",
                issue_category="UNKNOWN",
                confidence=0.60,
                reasoning=(
                    "Both error rate and latency increased during the incident window, "
                    "but no more specific resource or dependency signal was detected."
                ),
                supporting_signals=supporting_signals,
                next_checks=[
                    "Correlate with application logs.",
                    "Check downstream dependency metrics.",
                    "Check recent deployments.",
                    "Check traces for slow spans.",
                ],
                recommended_runbook_query="service degradation error rate latency spike",
                fallback_used=False,
            )

        return MetricsInsightResult(
            suspected_issue="No clear metric anomaly detected",
            issue_category="UNKNOWN",
            confidence=0.20,
            reasoning=(
                "Metrics did not contain a strong known signal pattern. "
                "Use logs, traces, deployments, and runbooks for further investigation."
            ),
            supporting_signals=supporting_signals,
            next_checks=[
                "Validate that required service metrics are available.",
                "Check logs for application-level errors.",
                "Check deployment history.",
                "Check distributed traces if available.",
            ],
            recommended_runbook_query="general production incident troubleshooting",
            fallback_used=True,
        )