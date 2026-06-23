from datetime import datetime, timedelta
import unittest
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(1, str(PROJECT_ROOT))

from incident_resolution_agent.analyzers.metrics_analyzer import (
    InMemoryMetricsProvider,
    MetricsAnalyzer,
)
from incident_resolution_agent.models.incident import IncidentAlert
from incident_resolution_agent.models.metric import MetricPoint, MetricSeries


def build_alert() -> IncidentAlert:
    return IncidentAlert(
        incident_id="INC-2001",
        service_name="payment-service",
        severity="HIGH",
        description="Payment failures increased suddenly",
        start_time=datetime.fromisoformat("2026-06-10T10:15:00"),
        end_time=datetime.fromisoformat("2026-06-10T10:45:00"),
    )


def build_series(
    metric_name: str,
    baseline_values: list[float],
    incident_values: list[float],
    unit: str,
    metadata: dict | None = None,
) -> MetricSeries:
    alert = build_alert()
    baseline_start = alert.start_time - (alert.end_time - alert.start_time)
    points = []

    for index, value in enumerate(baseline_values):
        points.append(
            MetricPoint(
                timestamp=baseline_start + timedelta(minutes=index * 10),
                value=value,
            )
        )

    for index, value in enumerate(incident_values):
        points.append(
            MetricPoint(
                timestamp=alert.start_time + timedelta(minutes=index * 10),
                value=value,
            )
        )

    return MetricSeries(
        name=metric_name,
        service_name=alert.service_name,
        unit=unit,
        points=points,
        source="unit-test",
        metadata=metadata or {},
    )


class MetricsAnalyzerTest(unittest.TestCase):
    def test_detects_metric_spikes_and_saturation(self) -> None:
        provider = InMemoryMetricsProvider(
            {
                "http.request.error_rate": [
                    build_series("http.request.error_rate", [1.0, 1.2, 1.1], [6.0, 7.0, 8.0], "%")
                ],
                "http.request.latency.p95": [
                    build_series("http.request.latency.p95", [180, 190, 200], [1100, 1300, 1200], "ms")
                ],
                "http.request.count": [
                    build_series("http.request.count", [1000, 1050, 980], [2100, 2200, 2300], "rpm")
                ],
                "system.cpu.usage": [
                    build_series("system.cpu.usage", [40, 42, 45], [88, 90, 91], "%")
                ],
                "system.memory.usage": [
                    build_series("system.memory.usage", [50, 55, 52], [70, 72, 74], "%")
                ],
                "db.connection.pool.active": [
                    build_series(
                        "db.connection.pool.active",
                        [30, 35, 32],
                        [92, 94, 95],
                        "connections",
                        metadata={"max_connections": 100},
                    )
                ],
                "db.connection.pool.pending": [
                    build_series("db.connection.pool.pending", [0, 0, 0], [12, 18, 16], "connections")
                ],
            }
        )

        result = MetricsAnalyzer(provider=provider).analyze(build_alert())

        signal_types = {signal.signal_type for signal in result.signals}
        self.assertEqual("payment-service", result.service_name)
        self.assertEqual(7, result.total_metrics)
        self.assertIn("ERROR_RATE_SPIKE", signal_types)
        self.assertIn("LATENCY_SPIKE", signal_types)
        self.assertIn("TRAFFIC_SPIKE", signal_types)
        self.assertIn("CPU_SATURATION", signal_types)
        self.assertIn("DB_POOL_ACTIVE_HIGH", signal_types)
        self.assertIn("DB_POOL_PENDING", signal_types)
        self.assertNotIn("MEMORY_PRESSURE", signal_types)
        self.assertFalse(result.fallback_used)
        self.assertFalse(result.missing_metrics)
        self.assertTrue(result.evidence)

    def test_tracks_missing_metrics(self) -> None:
        provider = InMemoryMetricsProvider(
            {
                "http.request.error_rate": [
                    build_series("http.request.error_rate", [1.0, 1.1, 1.2], [1.0, 1.1, 1.2], "%")
                ]
            }
        )

        result = MetricsAnalyzer(provider=provider).analyze(build_alert())

        self.assertEqual(1, result.total_metrics)
        self.assertEqual([], result.signals)
        self.assertGreater(len(result.missing_metrics), 0)
        self.assertFalse(result.fallback_used)


if __name__ == "__main__":
    unittest.main()
