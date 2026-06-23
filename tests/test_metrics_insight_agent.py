from datetime import datetime
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(1, str(PROJECT_ROOT))


from incident_resolution_agent.agents.metrics_insight_agent import MetricsInsightAgent
from incident_resolution_agent.models.metric import (
    MetricAnalysisResult,
    MetricSignal,
)


def build_signal(signal_type: str) -> MetricSignal:
    return MetricSignal(
        metric_name="test.metric",
        signal_type=signal_type,
        severity="WARN",
        summary=f"{signal_type} detected",
        baseline_value=10.0,
        incident_value=20.0,
        change_percent=100.0,
        evidence=[f"{signal_type} evidence"],
    )


def build_metric_analysis_result(signal_types: list[str]) -> MetricAnalysisResult:
    now = datetime.fromisoformat("2026-06-10T10:45:00")

    return MetricAnalysisResult(
        service_name="payment-service",
        baseline_window_start=now,
        baseline_window_end=now,
        analyzed_window_start=now,
        analyzed_window_end=now,
        total_metrics=len(signal_types),
        signals=[build_signal(signal_type) for signal_type in signal_types],
        evidence=[f"{signal_type} evidence" for signal_type in signal_types],
        missing_metrics=[],
        fallback_used=False,
    )


def test_detects_db_pool_saturation():
    agent = MetricsInsightAgent()

    result = agent.analyze(
        build_metric_analysis_result([
            "DB_POOL_ACTIVE_HIGH",
            "DB_POOL_PENDING",
            "LATENCY_SPIKE",
            "ERROR_RATE_SPIKE",
        ])
    )

    assert result.issue_category == "DATABASE"
    assert result.suspected_issue == "Possible database connection pool saturation"
    assert result.confidence == 0.85
    assert result.fallback_used is False


def test_no_metric_signal_returns_fallback():
    agent = MetricsInsightAgent()

    result = agent.analyze(build_metric_analysis_result([]))

    assert result.issue_category == "UNKNOWN"
    assert result.confidence == 0.20
    assert result.fallback_used is True