import json
from typing import Any

from incident_resolution_agent.models.incident import IncidentAlert
from incident_resolution_agent.models.log import LogAnalysisResult, LogInsightResult
from incident_resolution_agent.models.metric import MetricAnalysisResult, MetricsInsightResult
from incident_resolution_agent.models.report import IncidentReport
from incident_resolution_agent.models.runbook_models import RunbookResult


class RootCauseAgent:
    """
    Final reasoning layer for MVP 1.

    It consumes structured outputs from:
    - IncidentAlert
    - LogAnalysisResult
    - LogInsightResult
    - MetricsAnalysisResult
    - MetricsInsightResult
    - RunbookResult

    It produces:
    - IncidentReport

    MVP 1 rule:
    Do not invent metrics, deployment data, trace findings, Jira history,
    or Kubernetes state because those components are not available yet.
    """

    ALLOWED_CATEGORIES = {
        "DATABASE",
        "MEMORY",
        "KAFKA",
        "DOWNSTREAM_SERVICE",
        "AUTHENTICATION",
        "AUTHORIZATION",
        "RATE_LIMITING",
        "NETWORK",
        "DISK",
        "KUBERNETES",
        "UNKNOWN",
    }

    def __init__(self, llm: Any | None = None):
        self.llm = llm

    def generate_report(
        self,
        alert: IncidentAlert,
        log_analysis_result: LogAnalysisResult,
        log_insight_result: LogInsightResult,
        runbook_result: RunbookResult,
        metric_analysis_result:MetricAnalysisResult | None = None,
        metrics_insight_result: MetricsInsightResult | None = None,
    ) -> IncidentReport:
        base_confidence = self._calculate_base_confidence(
            log_analysis_result=log_analysis_result,
            log_insight_result=log_insight_result,
            runbook_result=runbook_result,
            metric_analysis_result=metric_analysis_result,
            metrics_insight_result=metrics_insight_result,
        )

        if self.llm is None:
            return self._fallback_report(
                alert=alert,
                log_analysis_result=log_analysis_result,
                log_insight_result=log_insight_result,
                runbook_result=runbook_result,
                metric_analysis_result=metric_analysis_result,
                metrics_insight_result=metrics_insight_result,
                confidence=base_confidence,
                fallback_reason="LLM was not configured.",
            )

        prompt = self._build_prompt(
            alert=alert,
            log_analysis_result=log_analysis_result,
            log_insight_result=log_insight_result,
            runbook_result=runbook_result,
            base_confidence=base_confidence,
            metric_analysis_result=metric_analysis_result,
            metrics_insight_result=metrics_insight_result,
        )

        try:
            response = self.llm.invoke(prompt)
            response_text = self._extract_response_text(response)
            parsed = self._parse_json_response(response_text)
            self._validate_response(parsed)

            return self._to_incident_report(
                alert=alert,
                data=parsed,
                confidence=base_confidence,
            )

        except Exception as ex:
            return self._fallback_report(
                alert=alert,
                log_analysis_result=log_analysis_result,
                log_insight_result=log_insight_result,
                runbook_result=runbook_result,
                metric_analysis_result=metric_analysis_result,
                metrics_insight_result=metrics_insight_result,
                confidence=base_confidence,
                fallback_reason=f"LLM report generation failed: {ex}",
            )

    def _calculate_base_confidence(
        self,
        log_analysis_result: LogAnalysisResult,
        log_insight_result: LogInsightResult,
        runbook_result: RunbookResult,
        metric_analysis_result: MetricAnalysisResult | None = None,
        metrics_insight_result: MetricsInsightResult | None = None,
    ) -> float:
        evidence_strength = self._calculate_evidence_strength(log_analysis_result)

        metrics_confidence = (
            metrics_insight_result.confidence
            if metrics_insight_result
            else 0.0
        )

        if metrics_insight_result:
            confidence = (
                log_insight_result.confidence * 0.40
                + metrics_confidence * 0.30
                + runbook_result.confidence * 0.20
                + evidence_strength * 0.10
            )
        else:
            confidence = (
                log_insight_result.confidence * 0.60
                + runbook_result.confidence * 0.30
                + evidence_strength * 0.10
            )

        if metrics_insight_result:
            if log_insight_result.issue_category == metrics_insight_result.issue_category:
                confidence += 0.08
            elif metrics_insight_result.issue_category != "UNKNOWN":
                confidence -= 0.05

        if log_insight_result.fallback_used:
            confidence -= 0.10

        if runbook_result.fallback_used:
            confidence -= 0.10

        if metrics_insight_result and metrics_insight_result.fallback_used:
            confidence -= 0.05

        return round(max(0.0, min(confidence, 1.0)), 2)

    def _calculate_evidence_strength(self, log_analysis_result: LogAnalysisResult) -> float:
        if log_analysis_result.error_count >= 100 and log_analysis_result.top_errors:
            return 0.90

        if log_analysis_result.error_count >= 20:
            return 0.70

        if log_analysis_result.warning_count >= 20:
            return 0.50

        if log_analysis_result.error_count > 0 or log_analysis_result.warning_count > 0:
            return 0.40

        return 0.10

    def _build_prompt(
        self,
        alert: IncidentAlert,
        log_analysis_result: LogAnalysisResult,
        log_insight_result: LogInsightResult,
        runbook_result: RunbookResult,
        base_confidence: float,
        metric_analysis_result: MetricAnalysisResult | None = None,
        metrics_insight_result: MetricsInsightResult | None = None,
    ) -> str:
        evidence = self._build_evidence(
            log_analysis_result=log_analysis_result,
            log_insight_result=log_insight_result,
            runbook_result=runbook_result,
        )

        return f"""
You are a production incident root cause assistant.

Your job:
Generate a careful, evidence-backed incident report.

Important rules:
- Use only the provided evidence.
- Do not invent metrics, deployment history, traces, Jira tickets, Kubernetes state, or database metrics.
- Do not claim a final root cause with certainty.
- Use phrases like "likely", "probable", or "suggests" when evidence is incomplete.
- If recommending rollback, make it conditional on confirming a recent deployment or configuration change.
- Return only valid JSON.
- Do not include markdown.

Incident:
incident_id: {alert.incident_id}
service_name: {alert.service_name}
severity: {alert.severity}
description: {alert.description}
start_time: {alert.start_time}
end_time: {alert.end_time}

Log analysis:
total_logs: {log_analysis_result.total_logs}
error_count: {log_analysis_result.error_count}
warning_count: {log_analysis_result.warning_count}
top_errors:
{self._format_top_errors(log_analysis_result)}

Log insight:
suspected_issue: {log_insight_result.suspected_issue}
issue_category: {log_insight_result.issue_category}
confidence: {log_insight_result.confidence}
reasoning: {log_insight_result.reasoning}
next_checks:
{self._format_list(log_insight_result.next_checks)}

Runbook result:
matched_runbooks: {runbook_result.matched_runbooks}
runbook_confidence: {runbook_result.confidence}
source_documents: {runbook_result.source_documents}
summary: {runbook_result.summary}
relevant_steps:
{self._format_list(runbook_result.relevant_steps)}
cautions:
{self._format_list(runbook_result.cautions)}

Computed base confidence:
{base_confidence}

Evidence to use:
{self._format_list(evidence)}

Missing signals to mention:
{self._format_list(self._default_missing_signals())}

Metrics analysis:
{self._format_metric_analysis(metric_analysis_result)}

Metrics insight:
{self._format_metrics_insight(metrics_insight_result)}

Return JSON exactly in this format:
{{
  "probable_root_cause": "careful probable root cause",
  "issue_category": "DATABASE",
  "evidence": ["evidence 1", "evidence 2"],
  "recommended_actions": ["action 1", "action 2"],
  "cautions": ["caution 1"],
  "missing_signals": ["missing signal 1"],
  "human_summary": "short human-readable summary"
}}
"""

    def _build_evidence(
        self,
        log_analysis_result: LogAnalysisResult,
        log_insight_result: LogInsightResult,
        runbook_result: RunbookResult,
        metric_analysis_result: MetricAnalysisResult | None = None,
        metrics_insight_result: MetricsInsightResult | None = None,
    ) -> list[str]:
        evidence = [
            f"{log_analysis_result.error_count} ERROR logs and "
            f"{log_analysis_result.warning_count} WARN logs were found for "
            f"{log_analysis_result.service_name} during the incident window."
        ]

        for error in log_analysis_result.top_errors[:5]:
            evidence.append(
                f"Top error pattern: '{error.message_pattern}' occurred {error.count} times."
            )

        if log_analysis_result.evidence:
            evidence.append(f"Representative log evidence: {log_analysis_result.evidence[0]}")

        evidence.append(
            f"Log Insight Agent suspected: {log_insight_result.suspected_issue} "
            f"with confidence {log_insight_result.confidence}."
        )

        if log_insight_result.reasoning:
            evidence.append(f"Log insight reasoning: {log_insight_result.reasoning}")

        if metrics_insight_result:
            evidence.append(
                f"Metrics Insight Agent suspected: {metrics_insight_result.suspected_issue} "
                f"with confidence {metrics_insight_result.confidence}."
            )

        if metrics_insight_result.reasoning:
            evidence.append(f"Metrics insight reasoning: {metrics_insight_result.reasoning}")

        if metric_analysis_result and metric_analysis_result.signals:
            for signal in metric_analysis_result.signals[:5]:
                evidence.append(f"Metric signal: {signal.summary}")

        if runbook_result.matched_runbooks:
            evidence.append("Matched runbook(s): " + ", ".join(runbook_result.matched_runbooks))

        if runbook_result.summary:
            evidence.append(f"Runbook summary: {runbook_result.summary}")

        return evidence

    def _format_top_errors(self, log_analysis_result: LogAnalysisResult) -> str:
        if not log_analysis_result.top_errors:
            return "- No grouped errors available."

        lines = []
        for error in log_analysis_result.top_errors:
            lines.append(
                f"- {error.message_pattern} | count={error.count} | "
                f"first_seen={error.first_seen} | last_seen={error.last_seen}"
            )

        return "\n".join(lines)

    def _format_list(self, items: list[str]) -> str:
        if not items:
            return "- None"
        return "\n".join(f"- {item}" for item in items)

    def _default_missing_signals(
        self,
        metric_analysis_result: MetricAnalysisResult | None = None,
    ) -> list[str]:
        missing = []

        if metric_analysis_result is None:
            missing.append("Metrics data was not analyzed.")

        missing.extend(
            [
                "Recent deployment or configuration history was not analyzed.",
                "Distributed traces were not analyzed.",
                "Infrastructure and Kubernetes events were not analyzed.",
            ]
        )

        return missing

    def _extract_response_text(self, response: Any) -> str:
        if isinstance(response, str):
            return response
        if hasattr(response, "content"):
            return response.content
        return str(response)

    def _parse_json_response(self, response_text: str) -> dict:
        response_text = response_text.strip()

        if response_text.startswith("```json"):
            response_text = response_text.replace("```json", "").replace("```", "").strip()
        elif response_text.startswith("```"):
            response_text = response_text.replace("```", "").strip()

        return json.loads(response_text)

    def _validate_response(self, data: dict) -> None:
        required_fields = [
            "probable_root_cause",
            "issue_category",
            "evidence",
            "recommended_actions",
            "cautions",
            "missing_signals",
            "human_summary",
        ]

        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")

        issue_category = str(data["issue_category"]).upper()
        if issue_category not in self.ALLOWED_CATEGORIES:
            raise ValueError(f"Invalid issue category: {issue_category}")

        for field in ["evidence", "recommended_actions", "cautions", "missing_signals"]:
            if not isinstance(data[field], list):
                raise ValueError(f"{field} must be a list")

        if not str(data["probable_root_cause"]).strip():
            raise ValueError("probable_root_cause cannot be empty")

        if not str(data["human_summary"]).strip():
            raise ValueError("human_summary cannot be empty")

        self._validate_rollback_language(data["recommended_actions"])

    def _validate_rollback_language(self, recommended_actions: list[str]) -> None:
        for action in recommended_actions:
            lower = action.lower()
            if "rollback" in lower and not (
                "if" in lower
                or "confirm" in lower
                or "confirmed" in lower
                or "after verifying" in lower
            ):
                raise ValueError("Rollback recommendation must be conditional in MVP 1.")

    def _to_incident_report(
        self,
        alert: IncidentAlert,
        data: dict,
        confidence: float,
    ) -> IncidentReport:
        return IncidentReport(
            incident_id=alert.incident_id,
            service_name=alert.service_name,
            severity=alert.severity,
            probable_root_cause=data["probable_root_cause"],
            issue_category=str(data["issue_category"]).upper(),
            confidence=confidence,
            evidence=data["evidence"],
            recommended_actions=data["recommended_actions"],
            cautions=data["cautions"],
            missing_signals=data["missing_signals"],
            human_summary=data["human_summary"],
            fallback_used=False,
        )

    def _fallback_report(
        self,
        alert: IncidentAlert,
        log_analysis_result: LogAnalysisResult,
        log_insight_result: LogInsightResult,
        runbook_result: RunbookResult,
        metric_analysis_result: MetricAnalysisResult | None,
        metrics_insight_result: MetricsInsightResult | None,
        confidence: float,
        fallback_reason: str,
    ) -> IncidentReport:
        evidence = self._build_evidence(
            log_analysis_result=log_analysis_result,
            log_insight_result=log_insight_result,
            runbook_result=runbook_result,
            metric_analysis_result=metric_analysis_result,
            metrics_insight_result=metrics_insight_result,
        )

        recommended_actions = self._deduplicate(
            log_insight_result.next_checks
            + (metrics_insight_result.next_checks if metrics_insight_result else [])
            + runbook_result.relevant_steps
        )

        if not recommended_actions:
            recommended_actions = [
                "Review application logs around the incident window.",
                "Check service health and dependency availability.",
                "Escalate to the service owner if the issue persists.",
            ]

        if (
            metrics_insight_result
            and metrics_insight_result.issue_category == log_insight_result.issue_category
            and metrics_insight_result.issue_category != "UNKNOWN"
        ):
            probable_root_cause = (
                f"{log_insight_result.suspected_issue}; metrics also suggest "
                f"{metrics_insight_result.suspected_issue}."
            )
        elif log_insight_result.suspected_issue:
            probable_root_cause = log_insight_result.suspected_issue
        elif metrics_insight_result:
            probable_root_cause = metrics_insight_result.suspected_issue
        else:
            probable_root_cause = "Unable to determine a probable root cause from available evidence."

        human_summary = (
            f"The available evidence suggests: {probable_root_cause}. "
            f"This report was generated using fallback logic. Reason: {fallback_reason}"
        )

        return IncidentReport(
            incident_id=alert.incident_id,
            service_name=alert.service_name,
            severity=alert.severity,
            probable_root_cause=probable_root_cause,
            issue_category=log_insight_result.issue_category,
            confidence=confidence,
            evidence=evidence,
            recommended_actions=recommended_actions,
            cautions=runbook_result.cautions,
            missing_signals=self._default_missing_signals(metric_analysis_result=metric_analysis_result),
            human_summary=human_summary,
            fallback_used=True,
        )

    def _deduplicate(self, items: list[str]) -> list[str]:
        result = []
        seen = set()

        for item in items:
            normalized = item.strip().lower()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            result.append(item)

        return result


def _format_metric_analysis(
    self,
    metric_analysis_result: MetricAnalysisResult | None,
) -> str:
    if metric_analysis_result is None:
        return "Metrics were not analyzed."

    if not metric_analysis_result.signals:
        return "Metrics were analyzed, but no strong metric anomaly was detected."

    lines = []
    for signal in metric_analysis_result.signals:
        lines.append(
            f"- {signal.signal_type} | metric={signal.metric_name} | "
            f"severity={signal.severity} | summary={signal.summary}"
        )

    return "\n".join(lines)


def _format_metrics_insight(
    self,
    metrics_insight_result: MetricsInsightResult | None,
) -> str:
    if metrics_insight_result is None:
        return "Metrics insight was not generated."

    return (
        f"suspected_issue: {metrics_insight_result.suspected_issue}\n"
        f"issue_category: {metrics_insight_result.issue_category}\n"
        f"confidence: {metrics_insight_result.confidence}\n"
        f"reasoning: {metrics_insight_result.reasoning}\n"
        f"next_checks:\n{self._format_list(metrics_insight_result.next_checks)}"
    )