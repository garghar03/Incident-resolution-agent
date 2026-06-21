from dataclasses import dataclass, field
from typing import Optional

from .incident import IncidentAlert
from .log import LogAnalysisResult, LogInsightResult
from .report import IncidentReport
from .runbook_models import RunbookResult


@dataclass
class IncidentWorkflowState:
    alert: IncidentAlert
    log_analysis_result: Optional[LogAnalysisResult] = None
    log_insight_result: Optional[LogInsightResult] = None
    runbook_result: Optional[RunbookResult] = None
    incident_report: Optional[IncidentReport] = None
    errors: list[str] = field(default_factory=list)
