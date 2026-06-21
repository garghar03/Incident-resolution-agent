from incident_resolution_agent.models.log import LogAnalysisResult

from .log_analyzer import BaseLogAnalyzer


class SplunkLogAnalyzer(BaseLogAnalyzer):
    def __init__(self, client):
        self.client = client

    def analyze_search(self, search_query: str) -> LogAnalysisResult:
        events = self.client.search(search_query)
        return self.analyze(events)
