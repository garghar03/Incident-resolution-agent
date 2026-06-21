from datetime import datetime

from incident_resolution_agent.agents.log_insight_agent import LogInsightAgent
from incident_resolution_agent.agents.root_cause_agent import RootCauseAgent
from incident_resolution_agent.analyzers.log_analyzer import BaseLogAnalyzer
from incident_resolution_agent.incident_orchestrator import IncidentOrchestrator
from incident_resolution_agent.models.incident import IncidentAlert
from incident_resolution_agent.rag.retrieval.runbook_retrieval_agent import RunbookRetrievalAgent


class EmptyRunbookRetriever:
    def search(self, query: str, top_k: int = 3, category: str | None = None):
        return []


def build_demo_orchestrator() -> IncidentOrchestrator:
    return IncidentOrchestrator(
        log_analyzer=BaseLogAnalyzer(),
        log_insight_agent=LogInsightAgent(llm=None),
        runbook_retrieval_agent=RunbookRetrievalAgent(
            retriever=EmptyRunbookRetriever(),
            llm=None,
        ),
        root_cause_agent=RootCauseAgent(llm=None),
    )


def build_demo_alert() -> IncidentAlert:
    return IncidentAlert(
        incident_id="INC-DEMO-001",
        service_name="payment-service",
        severity="HIGH",
        description="Payment failures increased suddenly",
        start_time=datetime.fromisoformat("2026-06-10T10:15:00"),
        end_time=datetime.fromisoformat("2026-06-10T10:45:00"),
    )


def main() -> None:
    report = build_demo_orchestrator().handle_incident(build_demo_alert())
    print(report.human_summary)


if __name__ == "__main__":
    main()
