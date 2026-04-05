import requests
from config import PROMETHEUS_URL


class PrometheusClient:
    def __init__(self):
        self.base_url = PROMETHEUS_URL

    def query(self, query: str):
        url = f"{self.base_url}/api/v1/query"
        params = {"query": query}

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            return data
        except Exception as e:
            print(f"[ERROR] Prometheus query failed: {e}")
            return None

    def extract_value(self, result_json):
        """
        Extracts numeric values from Prometheus response
        """

        if not result_json:
            return 0.0

        try:
            results = result_json["data"]["result"]

            if not results:
                return 0.0

            values = []

            for r in results:
                value = float(r["value"][1])
                values.append(value)

            # Aggregate (sum across pods)
            return sum(values)

        except Exception as e:
            print(f"[ERROR] Value extraction failed: {e}")
            return 0.0

    def get_metric(self, query: str):
        result = self.query(query)
        return self.extract_value(result)
