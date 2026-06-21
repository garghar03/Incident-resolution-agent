from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class LogQuery:
    service_name: str
    start_time: datetime
    end_time: datetime
    level: Optional[str] = None
    keyword: Optional[str] = None


@dataclass
class LogEvent:
    timestamp: datetime
    service_name: str
    level: str
    message: str
    source: str
    trace_id: str | None = None
    correlation_id: str | None = None
    metadata: dict | None = None


@dataclass
class GroupedError:
    message_pattern: str
    count: int
    first_seen: datetime | None
    last_seen: datetime | None


@dataclass
class LogAnalysisResult:
    service_name: str
    total_logs: int
    error_count: int
    warning_count: int
    top_errors: list[GroupedError]
    evidence: list[str]
    trace_ids: list[str]


@dataclass
class LogInsightResult:
    suspected_issue: str
    issue_category: str
    confidence: float
    reasoning: str
    next_checks: List[str]
    recommended_runbook_query: str
    recommended_next_agents: List[str]
    fallback_used: bool = False
