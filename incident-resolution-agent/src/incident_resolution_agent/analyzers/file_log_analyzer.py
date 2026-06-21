from .log_analyzer import BaseLogAnalyzer, LogAnalysisResult


class NFSLogAnalyzer(BaseLogAnalyzer):
    def analyze_file(self, path: str) -> LogAnalysisResult:
        with open(path, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]

        return self.analyze(lines)
