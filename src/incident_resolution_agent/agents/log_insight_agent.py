from incident_resolution_agent.models.log import LogAnalysisResult, LogInsightResult
from typing import Any
import json

class LogInsightAgent:

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
        "UNKNOWN"
    }

    def __init__(self, llm):
        self.llm = llm

    def analyze(self, log_result: LogAnalysisResult) -> LogInsightResult:
        return self.analyze_logs(log_result)

    def analyze_logs(self, log_result:LogAnalysisResult) -> LogInsightResult:     
        """Analyze structured log findings and 
        infer the most likely technical issue.
        this is the main method used by orchestatror
        """

        if self._has_no_useful_logs(log_result):
            return self._no_signal_result(log_result)

        prompt = self._build_prompt(log_result)
        try:
            result = self.llm.invoke(prompt)

            response_text = self._extract_response_text(result)

            parsed_result = self._parse_json_response(response_text)

            self._validate_response(parsed_result)

            return self._to_log_insight_result(parsed_result)
        
        except Exception as e:
            print(f"Error in LogInsightAgent: {e}")
            print("Falling back to basic insight result with limited information.")
            return self._fallback_result(log_result)
        

    def _has_no_useful_logs(self, log_result: LogAnalysisResult) -> bool:
        return (
            log_result.error_count == 0
            and log_result.warning_count == 0
            and not log_result.top_errors
        )


    def _build_prompt(self, log_result: LogAnalysisResult) -> str:
        top_errors_text = self._format_top_errors(log_result)
        evidence_text = self._format_evidence(log_result)

        return f"""
            You are a production incident log insight agent.

            Your job:
            Analyze structured log findings and infer the most likely technical issue.

            Rules:
            - Use only the provided log findings.
            - Do not invent deployment, metrics, or trace information.
            - Do not claim final root cause.
            - If evidence is weak, lower confidence.
            - Return only valid JSON.

            Allowed issue_category values:
            DATABASE, MEMORY, KAFKA, DOWNSTREAM_SERVICE, AUTHENTICATION,
            AUTHORIZATION, RATE_LIMITING, NETWORK, DISK, KUBERNETES, UNKNOWN

            Service: {log_result.service_name}
            Total logs: {log_result.total_logs}
            Error count: {log_result.error_count}
            Warning count: {log_result.warning_count}

            Top errors:
            {top_errors_text}

            Evidence:
            {evidence_text}

            Trace IDs:
            {log_result.trace_ids}

            Return JSON exactly in this format:
            {{
            "suspected_issue": "short suspected issue",
            "issue_category": "DATABASE",
            "confidence": 0.0,
            "reasoning": "why this issue is suspected",
            "next_checks": ["check 1", "check 2"],
            "recommended_runbook_query": "good query for runbook search",
            "recommended_next_agents": ["runbook_rag_agent"]
            }}
            """

    def _format_top_errors(self, log_result: LogAnalysisResult) -> str:
        if not log_result.top_errors:
            return "No grouped error found."

        lines = []
        for error in log_result.top_errors:
            lines.append(
                f"- {error.message_pattern} | count={error.count} | "
                f"first_seen={error.first_seen} | last_seen={error.last_seen}"
            )

        return "\n".join(lines)

    def _format_evidence(self, log_result: LogAnalysisResult) -> str:
        if not log_result.evidence:
            return "No evidence log lines available."

        limited_evidence = log_result.evidence[:10]

        return "\n".join(f"- {line}" for line in limited_evidence)
    
    
    def _no_signal_result(self, log_result: LogAnalysisResult) -> LogInsightResult:
        return LogInsightResult(
            suspected_issue="No clear issue detected from logs",
            issue_category="UNKNOWN",
            confidence=0.0,
            reasoning="No error or warning logs found in the given time frame.",
            next_checks=["Check other data sources like metrics or traces for anomalies."],
            recommended_runbook_query="",
            recommended_next_agents=[]
        )
        
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
            "suspected_issue",
            "issue_category",
            "confidence",
            "reasoning",
            "next_checks",
            "recommended_runbook_query",
            "recommended_next_agents"
        ]

        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")

        if data["issue_category"] not in self.ALLOWED_CATEGORIES:
            raise ValueError(f"Invalid issue category: {data['issue_category']}")

        confidence = float(data["confidence"])

        if confidence < 0.0 or confidence > 1.0:
            raise ValueError("Confidence must be between 0 and 1")

        if not isinstance(data["next_checks"], list):
            raise ValueError("next_checks must be a list")

        if not isinstance(data["recommended_next_agents"], list):
            raise ValueError("recommended_next_agents must be a list")

        if not data["recommended_runbook_query"]:
            raise ValueError("recommended_runbook_query cannot be empty")


    def _to_log_insight_result(self, data: dict) -> LogInsightResult:
        return LogInsightResult(
            suspected_issue=data["suspected_issue"],
            issue_category=data["issue_category"],
            confidence=float(data["confidence"]),
            reasoning=data["reasoning"],
            next_checks=data["next_checks"],
            recommended_runbook_query=data["recommended_runbook_query"],
            recommended_next_agents=data["recommended_next_agents"],
            fallback_used=False
        )
        
    def _fallback_result(self, log_result: LogAnalysisResult) -> LogInsightResult:
        error_text = " ".join(
            error.message_pattern.lower()
            for error in log_result.top_errors
        )

        if "hikari" in error_text or "sqltransientconnectionexception" in error_text:
            return LogInsightResult(
                suspected_issue="Possible DB connection pool exhaustion",
                issue_category="DATABASE",
                confidence=0.70,
                reasoning="Repeated database connection timeout patterns were detected in grouped errors.",
                next_checks=[
                    "Check Hikari active and idle connection metrics",
                    "Check database max connection usage",
                    "Check slow queries",
                    "Check recent connection pool configuration changes"
                ],
                recommended_runbook_query="DB connection pool exhaustion Hikari SQLTransientConnectionException",
                recommended_next_agents=["runbook_rag_agent"],
                fallback_used=True
            )

        if "outofmemory" in error_text or "heap space" in error_text:
            return LogInsightResult(
                suspected_issue="Possible memory issue",
                issue_category="MEMORY",
                confidence=0.70,
                reasoning="Memory-related error patterns were detected in grouped errors.",
                next_checks=[
                    "Check heap usage",
                    "Check GC logs",
                    "Check memory limits",
                    "Check recent memory-intensive changes"
                ],
                recommended_runbook_query="OutOfMemoryError heap memory issue",
                recommended_next_agents=["runbook_rag_agent"],
                fallback_used=True
            )

        if "connection refused" in error_text or "read timed out" in error_text:
            return LogInsightResult(
                suspected_issue="Possible downstream service connectivity issue",
                issue_category="DOWNSTREAM_SERVICE",
                confidence=0.65,
                reasoning="Connectivity-related error patterns were detected in grouped errors.",
                next_checks=[
                    "Check downstream service health",
                    "Check network connectivity",
                    "Check timeout settings",
                    "Check dependency availability"
                ],
                recommended_runbook_query="downstream service timeout connection refused",
                recommended_next_agents=["runbook_rag_agent"],
                fallback_used=True
            )

        if "kafka" in error_text or "consumer lag" in error_text:
            return LogInsightResult(
                suspected_issue="Possible Kafka consumer issue",
                issue_category="KAFKA",
                confidence=0.65,
                reasoning="Kafka-related error patterns were detected in grouped errors.",
                next_checks=[
                    "Check Kafka consumer lag",
                    "Check broker health",
                    "Check partition assignment",
                    "Check consumer group rebalancing"
                ],
                recommended_runbook_query="Kafka consumer lag broker rebalance issue",
                recommended_next_agents=["runbook_rag_agent"],
                fallback_used=True
            )

        return LogInsightResult(
            suspected_issue="Unknown issue from logs",
            issue_category="UNKNOWN",
            confidence=0.30,
            reasoning="No strong known error pattern was detected from grouped log errors.",
            next_checks=[
                "Expand log search window",
                "Check metrics",
                "Check distributed traces",
                "Check recent deployments"
            ],
            recommended_runbook_query="general production incident troubleshooting",
            recommended_next_agents=["runbook_rag_agent"],
            fallback_used=True
        )
