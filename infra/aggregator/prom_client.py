import requests
from config import (
    PROMETHEUS_URL,
    REQUEST_RATE_QUERY,
    CPU_USAGE_QUERY,
    MEMORY_USAGE_QUERY,
    CPU_P95_QUERY,
    MEMORY_P95_QUERY
)


class PrometheusClient:
    def __init__(self):
        self.base_url = PROMETHEUS_URL

    def _query(self, query):
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/query",
                params={"query": query},
                timeout=5
            )
            data = response.json()

            if data["status"] != "success":
                return []

            return data["data"]["result"]

        except Exception as e:
            print(f"❌ Prometheus query failed: {e}")
            return []

    def _extract_value(self, result, default=0.0):
        """
        Extract numeric value safely from Prometheus response.

        WHY default=0.0:
          If Prometheus returns empty (not enough history yet,
          pod restarted, scrape gap), we return 0.0 so the
          safety guard simply falls back to the raw prediction
          via max(pred, 0.0) = pred. No crash, no stale data.
        """
        try:
            if not result:
                return default

            return float(result[0]["value"][1])

        except Exception:
            return default

    # -------------------------------
    # REAL-TIME METRICS
    # -------------------------------

    def get_metrics(self):
        req = self._query(REQUEST_RATE_QUERY)
        cpu = self._query(CPU_USAGE_QUERY)
        mem = self._query(MEMORY_USAGE_QUERY)

        return {
            "request_rate": self._extract_value(req),
            "cpu_usage": self._extract_value(cpu),
            "memory_usage": self._extract_value(mem)
        }

    # -------------------------------
    # SAFETY BASELINE (P95)
    #
    # WHY separate method:
    #   P95 queries are heavier (range queries over 5m).
    #   Keeping them separate lets us call them independently
    #   and makes the main loop easier to reason about.
    #   If this call fails entirely, the caller gets 0.0 defaults
    #   and the system degrades gracefully to raw predictions.
    # -------------------------------

    def get_p95_metrics(self):
        cpu_p95 = self._query(CPU_P95_QUERY)
        mem_p95 = self._query(MEMORY_P95_QUERY)

        result = {
            "cpu_p95": self._extract_value(cpu_p95, default=0.0),
            "memory_p95": self._extract_value(mem_p95, default=0.0)
        }

        # Warn if p95 came back empty — useful for debugging cold-start
        if result["cpu_p95"] == 0.0:
            print("⚠️  cpu_p95 returned 0.0 — not enough history yet or query failed")
        if result["memory_p95"] == 0.0:
            print("⚠️  memory_p95 returned 0.0 — not enough history yet or query failed")

        return result
