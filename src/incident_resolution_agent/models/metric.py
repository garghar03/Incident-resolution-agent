from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class MetricPoint:
    timestamp: datetime
    value: float


@dataclass
class MetricSeries:
    name: str
    service_name: str
    unit: str
    points: list[MetricPoint]
    source: str = "unknown"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MetricSignal:
    metric_name: str
    signal_type: str
    severity: str
    summary: str
    baseline_value: float | None
    incident_value: float | None
    change_percent: float | None
    evidence: list[str]


@dataclass
class MetricAnalysisResult:
    service_name: str
    baseline_window_start: datetime
    baseline_window_end: datetime
    analyzed_window_start: datetime
    analyzed_window_end: datetime
    total_metrics: int
    signals: list[MetricSignal]
    evidence: list[str]
    missing_metrics: list[str]
    fallback_used: bool = False


@dataclass
class MetricsInsightResult:
    suspected_issue: str
    issue_category: str
    confidence: float
    reasoning: str
    supporting_signals: list[str]
    next_checks: list[str]
    recommended_runbook_query: str
    fallback_used: bool = False