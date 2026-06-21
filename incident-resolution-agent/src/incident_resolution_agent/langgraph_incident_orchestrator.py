from typing import Any

from incident_resolution_agent.incident_orchestrator import IncidentOrchestrator
from incident_resolution_agent.models.incident import IncidentAlert
from incident_resolution_agent.models.incident_workflow_state import IncidentWorkflowState
from incident_resolution_agent.models.report import IncidentReport


class LangGraphIncidentOrchestrator(IncidentOrchestrator):
    """
    LangGraph-backed workflow when LangGraph is installed.

    If LangGraph is not available, the class still works by using the same
    deterministic orchestration path as IncidentOrchestrator. This keeps local
    MVP demos runnable in lightweight environments.
    """

    def __init__(
        self,
        log_analyzer,
        log_insight_agent,
        runbook_retrieval_agent,
        root_cause_agent,
    ):
        super().__init__(
            log_analyzer=log_analyzer,
            log_insight_agent=log_insight_agent,
            runbook_retrieval_agent=runbook_retrieval_agent,
            root_cause_agent=root_cause_agent,
        )
        self.graph = self._build_graph()

    def handle_incident(self, alert: IncidentAlert) -> IncidentReport:
        if self.graph is None:
            return super().handle_incident(alert)

        initial_state = IncidentWorkflowState(alert=alert)
        final_state = self.graph.invoke(initial_state)

        if isinstance(final_state, dict):
            report = final_state.get("incident_report")
        else:
            report = final_state.incident_report

        if report is None:
            return self._build_failure_report(alert, "LangGraph workflow finished without a report.")

        return report

    def _build_graph(self) -> Any | None:
        try:
            from langgraph.graph import END, START, StateGraph
        except Exception:
            return None

        builder = StateGraph(IncidentWorkflowState)
        builder.add_node("validate_alert", self._validate_alert_node)
        builder.add_node("analyze_logs", self._analyze_logs_node)
        builder.add_node("generate_log_insight", self._generate_log_insight_node)
        builder.add_node("retrieve_runbook", self._retrieve_runbook_node)
        builder.add_node("generate_root_cause_report", self._generate_root_cause_report_node)
        builder.add_node("build_failure_report", self._build_failure_report_node)

        builder.add_edge(START, "validate_alert")
        builder.add_conditional_edges(
            "validate_alert",
            self._route_after_step,
            {"continue": "analyze_logs", "failure": "build_failure_report"},
        )
        builder.add_conditional_edges(
            "analyze_logs",
            self._route_after_step,
            {"continue": "generate_log_insight", "failure": "build_failure_report"},
        )
        builder.add_conditional_edges(
            "generate_log_insight",
            self._route_after_step,
            {"continue": "retrieve_runbook", "failure": "build_failure_report"},
        )
        builder.add_conditional_edges(
            "retrieve_runbook",
            self._route_after_step,
            {"continue": "generate_root_cause_report", "failure": "build_failure_report"},
        )
        builder.add_edge("generate_root_cause_report", END)
        builder.add_edge("build_failure_report", END)

        return builder.compile()

    def _validate_alert_node(self, state: IncidentWorkflowState) -> IncidentWorkflowState:
        validation_error = self._validate_alert(state.alert)
        if validation_error:
            state.errors.append(validation_error)
        return state

    def _analyze_logs_node(self, state: IncidentWorkflowState) -> IncidentWorkflowState:
        try:
            state.log_analysis_result = self.log_analyzer.analyze(state.alert)
        except Exception as exc:
            state.errors.append(f"Log analysis failed: {exc}")
        return state

    def _generate_log_insight_node(self, state: IncidentWorkflowState) -> IncidentWorkflowState:
        try:
            state.log_insight_result = self.log_insight_agent.analyze(state.log_analysis_result)
        except Exception as exc:
            state.errors.append(f"Log insight generation failed: {exc}")
        return state

    def _retrieve_runbook_node(self, state: IncidentWorkflowState) -> IncidentWorkflowState:
        try:
            request = self._build_runbook_request(state.log_insight_result)
            state.runbook_result = self.runbook_retrieval_agent.search(request)
        except Exception as exc:
            state.errors.append(f"Runbook retrieval failed: {exc}")
        return state

    def _generate_root_cause_report_node(
        self,
        state: IncidentWorkflowState,
    ) -> IncidentWorkflowState:
        try:
            state.incident_report = self.root_cause_agent.generate_report(
                alert=state.alert,
                log_analysis_result=state.log_analysis_result,
                log_insight_result=state.log_insight_result,
                runbook_result=state.runbook_result,
            )
        except Exception as exc:
            state.errors.append(f"Root cause report generation failed: {exc}")
            state.incident_report = self._build_failure_report(state.alert, state.errors[-1])
        return state

    def _build_failure_report_node(self, state: IncidentWorkflowState) -> IncidentWorkflowState:
        message = "; ".join(state.errors) if state.errors else "Incident workflow failed."
        state.incident_report = self._build_failure_report(state.alert, message)
        return state

    def _route_after_step(self, state: IncidentWorkflowState) -> str:
        return "failure" if state.errors else "continue"


__all__ = ["LangGraphIncidentOrchestrator"]
