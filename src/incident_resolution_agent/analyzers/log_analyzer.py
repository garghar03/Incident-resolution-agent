from collections import Counter
from typing import Sequence

from incident_resolution_agent.models.incident import IncidentAlert
from incident_resolution_agent.models.log import GroupedError, LogAnalysisResult


class BaseLogAnalyzer:
    def analyze(self, logs: Sequence[str] | IncidentAlert) -> LogAnalysisResult:
        if isinstance(logs, IncidentAlert):
            return LogAnalysisResult(
                service_name=logs.service_name,
                total_logs=0,
                error_count=0,
                warning_count=0,
                top_errors=[],
                evidence=[],
                trace_ids=[],
            )

        lines = [line.strip() for line in logs if line and line.strip()]
        errors = [line for line in lines if "ERROR" in line.upper()]
        warnings = [line for line in lines if "WARN" in line.upper()]

        grouped = [
            GroupedError(
                message_pattern=message,
                count=count,
                first_seen=None,
                last_seen=None,
            )
            for message, count in Counter(errors).most_common(5)
        ]

        return LogAnalysisResult(
            service_name="unknown",
            total_logs=len(lines),
            error_count=len(errors),
            warning_count=len(warnings),
            top_errors=grouped,
            evidence=errors[:20],
            trace_ids=[],
        )
