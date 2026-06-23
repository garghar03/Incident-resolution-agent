from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from incident_resolution_agent.models.incident import IncidentAlert
from incident_resolution_agent.models.metric import (
    MetricAnalysisResult,
    MetricPoint,
    MetricSeries,
    MetricSignal,
)


class MetricsProvider(Protocol):
    def fetch_series(
        self,
        service_name: str,
        metric_name: str,
        start_time: datetime,
        end_time: datetime,
    ) -> MetricSeries | None:
        ...


@dataclass(frozen=True)
class MetricRule:
    metric_name: str
    signal_type: str
    direction: str
    threshold_percent: float | None = None
    absolute_threshold: float | None = None


class InMemoryMetricsProvider:
    """Small provider for tests and local demos."""

    def __init__(self, series_by_metric: dict[str, list[MetricSeries]]):
        self.series_by_metric = series_by_metric

    def fetch_series(
        self,
        service_name: str,
        metric_name: str,
        start_time: datetime,
        end_time: datetime,
    ) -> MetricSeries | None:
        for series in self.series_by_metric.get(metric_name, []):
            if series.service_name != service_name:
                continue

            points = [
                point
                for point in series.points
                if start_time <= point.timestamp < end_time
            ]

            if not points:
                return None

            return MetricSeries(
                name=series.name,
                service_name=series.service_name,
                unit=series.unit,
                points=points,
                source=series.source,
                metadata=series.metadata,
            )

        return None


class MetricsAnalyzer:
    """
    Summarizes metric changes around an incident.

    The analyzer returns factual signals only. It does not infer final root cause.
    """

    DEFAULT_METRIC_NAMES = (
        "http.request.error_rate",
        "http.request.latency.p95",
        "http.request.count",
        "system.cpu.usage",
        "system.memory.usage",
        "db.connection.pool.active",
        "db.connection.pool.pending",
    )

    DEFAULT_RULES = (
        MetricRule(
            metric_name="http.request.error_rate",
            signal_type="ERROR_RATE_SPIKE",
            direction="increase",
            threshold_percent=50.0,
        ),
        MetricRule(
            metric_name="http.request.latency.p95",
            signal_type="LATENCY_SPIKE",
            direction="increase",
            threshold_percent=50.0,
        ),
        MetricRule(
            metric_name="http.request.count",
            signal_type="TRAFFIC_SPIKE",
            direction="increase",
            threshold_percent=50.0,
        ),
        MetricRule(
            metric_name="http.request.count",
            signal_type="TRAFFIC_DROP",
            direction="decrease",
            threshold_percent=50.0,
        ),
        MetricRule(
            metric_name="system.cpu.usage",
            signal_type="CPU_SATURATION",
            direction="above",
            absolute_threshold=85.0,
        ),
        MetricRule(
            metric_name="system.memory.usage",
            signal_type="MEMORY_PRESSURE",
            direction="above",
            absolute_threshold=85.0,
        ),
        MetricRule(
            metric_name="db.connection.pool.active",
            signal_type="DB_POOL_ACTIVE_HIGH",
            direction="above",
            absolute_threshold=85.0,
        ),
        MetricRule(
            metric_name="db.connection.pool.pending",
            signal_type="DB_POOL_PENDING",
            direction="above",
            absolute_threshold=0.0,
        ),
    )

    def __init__(
        self,
        provider: MetricsProvider,
        metric_names: list[str] | None = None,
        rules: list[MetricRule] | None = None,
    ):
        self.provider = provider
        self.metric_names = metric_names or list(self.DEFAULT_METRIC_NAMES)
        self.rules = rules or list(self.DEFAULT_RULES)

    def analyze(self, alert: IncidentAlert) -> MetricAnalysisResult:
        baseline_start, baseline_end = self._baseline_window(alert)
        signals: list[MetricSignal] = []
        evidence: list[str] = []
        missing_metrics: list[str] = []
        total_metrics = 0
        fallback_used = False

        for metric_name in self.metric_names:
            try:
                baseline_series = self.provider.fetch_series(
                    service_name=alert.service_name,
                    metric_name=metric_name,
                    start_time=baseline_start,
                    end_time=baseline_end,
                )
                incident_series = self.provider.fetch_series(
                    service_name=alert.service_name,
                    metric_name=metric_name,
                    start_time=alert.start_time,
                    end_time=alert.end_time,
                )
            except Exception as exc:
                fallback_used = True
                missing_metrics.append(f"{metric_name}: provider error: {exc}")
                continue

            if not baseline_series or not baseline_series.points:
                missing_metrics.append(f"{metric_name}: baseline data unavailable")
                continue

            if not incident_series or not incident_series.points:
                missing_metrics.append(f"{metric_name}: incident data unavailable")
                continue

            total_metrics += 1
            baseline_value = self._average(baseline_series.points)
            incident_value = self._average(incident_series.points)
            metric_signals = self._detect_signals(
                metric_name=metric_name,
                unit=incident_series.unit,
                baseline_value=baseline_value,
                incident_value=incident_value,
                metadata=incident_series.metadata,
            )
            signals.extend(metric_signals)
            evidence.extend(signal.evidence[0] for signal in metric_signals if signal.evidence)

        return MetricAnalysisResult(
            service_name=alert.service_name,
            baseline_window_start=baseline_start,
            baseline_window_end=baseline_end,
            analyzed_window_start=alert.start_time,
            analyzed_window_end=alert.end_time,
            total_metrics=total_metrics,
            signals=signals,
            evidence=evidence,
            missing_metrics=missing_metrics,
            fallback_used=fallback_used,
        )

    def _baseline_window(self, alert: IncidentAlert) -> tuple[datetime, datetime]:
        incident_duration = alert.end_time - alert.start_time
        return alert.start_time - incident_duration, alert.start_time

    def _detect_signals(
        self,
        metric_name: str,
        unit: str,
        baseline_value: float,
        incident_value: float,
        metadata: dict,
    ) -> list[MetricSignal]:
        matched_signals = []

        for rule in self._rules_for(metric_name):
            normalized_incident_value = self._normalize_incident_value(
                metric_name=metric_name,
                incident_value=incident_value,
                metadata=metadata,
            )

            if not self._rule_matches(
                rule=rule,
                baseline_value=baseline_value,
                incident_value=normalized_incident_value,
            ):
                continue

            change_percent = self._change_percent(
                baseline_value=baseline_value,
                incident_value=incident_value,
            )
            summary = self._build_summary(
                rule=rule,
                baseline_value=baseline_value,
                incident_value=incident_value,
                unit=unit,
                change_percent=change_percent,
                metadata=metadata,
            )

            matched_signals.append(
                MetricSignal(
                    metric_name=metric_name,
                    signal_type=rule.signal_type,
                    severity=self._severity(rule, change_percent, normalized_incident_value),
                    summary=summary,
                    baseline_value=round(baseline_value, 2),
                    incident_value=round(incident_value, 2),
                    change_percent=change_percent,
                    evidence=[summary],
                )
            )

        return matched_signals

    def _rules_for(self, metric_name: str) -> list[MetricRule]:
        return [rule for rule in self.rules if rule.metric_name == metric_name]

    def _rule_matches(
        self,
        rule: MetricRule,
        baseline_value: float,
        incident_value: float,
    ) -> bool:
        if rule.direction == "increase":
            return self._increase_percent(baseline_value, incident_value) >= (
                rule.threshold_percent or 0.0
            )

        if rule.direction == "decrease":
            return self._decrease_percent(baseline_value, incident_value) >= (
                rule.threshold_percent or 0.0
            )

        if rule.direction == "above":
            return incident_value > (rule.absolute_threshold or 0.0)

        return False

    def _normalize_incident_value(
        self,
        metric_name: str,
        incident_value: float,
        metadata: dict,
    ) -> float:
        if metric_name == "db.connection.pool.active":
            max_connections = metadata.get("max_connections")
            if max_connections:
                return (incident_value / float(max_connections)) * 100

        return incident_value

    def _build_summary(
        self,
        rule: MetricRule,
        baseline_value: float,
        incident_value: float,
        unit: str,
        change_percent: float | None,
        metadata: dict,
    ) -> str:
        change_text = (
            f"{change_percent}% change"
            if change_percent is not None
            else "change from zero baseline"
        )

        extra = ""
        if rule.metric_name == "db.connection.pool.active" and metadata.get("max_connections"):
            max_connections = float(metadata["max_connections"])
            utilization = round((incident_value / max_connections) * 100, 2)
            extra = f" ({utilization}% of configured max {max_connections:g})"

        return (
            f"{rule.signal_type}: {rule.metric_name} baseline average was "
            f"{round(baseline_value, 2)}{unit}, incident average was "
            f"{round(incident_value, 2)}{unit}{extra}; {change_text}."
        )

    def _severity(
        self,
        rule: MetricRule,
        change_percent: float | None,
        incident_value: float,
    ) -> str:
        if rule.direction == "above":
            if incident_value >= 95.0:
                return "CRITICAL"
            return "WARN"

        if change_percent is None:
            return "WARN"

        if change_percent >= 200.0:
            return "CRITICAL"

        return "WARN"

    def _average(self, points: list[MetricPoint]) -> float:
        return sum(point.value for point in points) / len(points)

    def _increase_percent(self, baseline_value: float, incident_value: float) -> float:
        if baseline_value == 0:
            return 100.0 if incident_value > 0 else 0.0

        return ((incident_value - baseline_value) / baseline_value) * 100

    def _decrease_percent(self, baseline_value: float, incident_value: float) -> float:
        if baseline_value == 0:
            return 0.0

        return ((baseline_value - incident_value) / baseline_value) * 100

    def _change_percent(
        self,
        baseline_value: float,
        incident_value: float,
    ) -> float | None:
        if baseline_value == 0:
            return None if incident_value > 0 else 0.0

        return round(((incident_value - baseline_value) / baseline_value) * 100, 2)
