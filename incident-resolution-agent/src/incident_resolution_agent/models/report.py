from dataclasses import dataclass
from typing import List


@dataclass
class IncidentReport:
    incident_id: str
    service_name: str
    probable_root_cause: str
    confidence: float
    evidence: List[str]
    recommended_actions: List[str]
    human_summary: str
    severity: str
    issue_category: str
    cautions: List[str]
    missing_signals: List[str]
    fallback_used: bool
