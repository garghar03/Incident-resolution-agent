from .log_analyzer import BaseLogAnalyzer, LogAnalysisResult


class LokiLogAnalyzer(BaseLogAnalyzer):
    def __init__(self, client):
        self.client = client

    def analyze_range(self, query: str, start: int, end: int) -> LogAnalysisResult:
        lines = self.client.query_range(query, start, end)
        return self.analyze(lines)
