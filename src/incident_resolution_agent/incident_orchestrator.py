from incident_resolution_agent.models.incident import IncidentAlert
from incident_resolution_agent.models.log import LogAnalysisResult, LogInsightResult
from incident_resolution_agent.models.metric import MetricsInsightResult
from incident_resolution_agent.models.report import IncidentReport
from incident_resolution_agent.models.runbook_models import RunbookResult, RunbookSearchRequest


class IncidentOrchestrator:
    """Coordinates the MVP 1 incident analysis workflow."""

    def __init__(
        self,
        log_analyzer,
        log_insight_agent,
        runbook_retrieval_agent,
        root_cause_agent,
        metrics_analyzer=None,
        metrics_insight_agent=None,
    ):
        self.log_analyzer = log_analyzer
        self.log_insight_agent = log_insight_agent
        self.runbook_retrieval_agent = runbook_retrieval_agent
        self.root_cause_agent = root_cause_agent
        self.metrics_analyzer = metrics_analyzer
        self.metrics_insight_agent = metrics_insight_agent

    def handle_incident(self, alert: IncidentAlert) -> IncidentReport:
        validation_error = self._validate_alert(alert)
        if validation_error:
            return self._build_failure_report(alert, validation_error)

        try:
            log_analysis_result = self.log_analyzer.analyze(alert)
            log_insight_result = self.log_insight_agent.analyze(log_analysis_result)

            metric_analysis_result = None
            metrics_insight_result = None

            if self.metrics_analyzer and self.metrics_insight_agent:
               metric_analysis_result = self.metrics_analyzer.analyze(alert)
               metrics_insight_result = self.metrics_insight_agent.analyze(
                   metric_analysis_result
               )

            runbook_request = self._build_runbook_request(
               log_insight_result=log_insight_result,
               metrics_insight_result=metrics_insight_result,
            )

            runbook_result = self.runbook_retrieval_agent.search(
                runbook_request
            )

            return self.root_cause_agent.generate_report(
                alert=alert,
                log_analysis_result=log_analysis_result,
                log_insight_result=log_insight_result,
                runbook_result=runbook_result,
                metric_analysis_result=metric_analysis_result,
                metrics_insight_result=metrics_insight_result,
            )

        except Exception as exc:
            return self._build_failure_report(alert, f"Incident workflow failed: {exc}")

    def _validate_alert(self, alert: IncidentAlert | None) -> str | None:
        if alert is None:
            return "Alert is required."

        if not alert.incident_id:
            return "Alert incident_id is required."

        if not alert.service_name:
            return "Alert service_name is required."

        if not alert.severity:
            return "Alert severity is required."

        if not alert.start_time or not alert.end_time:
            return "Alert start_time and end_time are required."

        if alert.end_time < alert.start_time:
            return "Alert end_time cannot be earlier than start_time."

        return None

    def _build_runbook_request(
        self,
        log_insight_result: LogInsightResult,
        metrics_insight_result: MetricsInsightResult | None,
    ) -> RunbookSearchRequest:
        query_parts = []

        if log_insight_result and log_insight_result.recommended_runbook_query:
            query_parts.append(log_insight_result.recommended_runbook_query)

        if metrics_insight_result and metrics_insight_result.recommended_runbook_query:
            query_parts.append(metrics_insight_result.recommended_runbook_query)    


        query = " ".join(query_parts).strip()

        if not query :
            query = (
                log_insight_result.suspected_issue
                if log_insight_result and log_insight_result.suspected_issue
                else "general production incident troubleshooting"
            )

        category = log_insight_result.issue_category
        confidence = log_insight_result.confidence

        if metrics_insight_result and metrics_insight_result.confidence > confidence:
            category = metrics_insight_result.issue_category
            confidence = metrics_insight_result.confidence

        return RunbookSearchRequest(
            query=query,
            top_k=3,
            category=category,
            insight_confidence=confidence,
        )

    def _build_failure_report(
        self,
        alert: IncidentAlert | None,
        message: str,
    ) -> IncidentReport:
        incident_id = alert.incident_id if alert else "UNKNOWN"
        service_name = alert.service_name if alert else "UNKNOWN"
        severity = alert.severity if alert else "UNKNOWN"

        return IncidentReport(
            incident_id=incident_id,
            service_name=service_name,
            severity=severity,
            probable_root_cause="Incident analysis could not be completed.",
            issue_category="UNKNOWN",
            confidence=0.0,
            evidence=[message],
            recommended_actions=[
                "Validate the alert payload and retry the workflow.",
                "Check component logs for the failing workflow step.",
            ],
            cautions=["Do not take remediation action based only on this failure report."],
            missing_signals=[
                "Log analysis was not completed.",
                "Runbook retrieval was not completed.",
                "Root cause report generation was not completed.",
            ],
            human_summary=message,
            fallback_used=True,
        )


__all__ = ["IncidentOrchestrator"]
