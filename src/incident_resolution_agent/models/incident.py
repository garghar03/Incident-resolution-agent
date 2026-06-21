from dataclasses import dataclass
from datetime import datetime

@dataclass
class IncidentAlert:
    incident_id: str
    service_name: str
    severity: str
    description: str
    start_time: datetime
    end_time: datetime
