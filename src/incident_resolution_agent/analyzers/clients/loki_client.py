class LokiClient:
    def __init__(self, endpoint: str, token: str = None):
        self.endpoint = endpoint
        self.token = token

    def query_range(self, query: str, start: int, end: int):
        try:
            import requests
        except ModuleNotFoundError as exc:
            raise RuntimeError("Install 'requests' to use LokiClient.") from exc

        params = {"query": query, "start": start, "end": end}
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        resp = requests.get(f"{self.endpoint}/loki/api/v1/query_range", params=params, headers=headers)
        resp.raise_for_status()

        data = resp.json()

        lines = []
        for stream in data.get("data", {}).get("result", []):
            for v in stream.get("values", []):
                lines.append(v[1])

        return lines
