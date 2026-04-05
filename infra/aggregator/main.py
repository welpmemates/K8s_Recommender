# Package inclusion
import sys
import os

# Add infra/ to Python path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import time
import numpy as np

# Prometheus
from prometheus_client import start_http_server, Gauge

# Your modules
from prom_client import PrometheusClient
from feature_builder import FeatureBuilder
from yaml_generator import generate_resources_yaml
from config import (
    QUERY_INTERVAL,
    REQUEST_RATE_QUERY,
    CPU_USAGE_QUERY,
    MEMORY_USAGE_QUERY,
    WINDOW_SIZE
)

from ml.trainer import OnlineTrainer
from ml.dataset import build_sample
from ml.utils import format_prediction


# -------------------------------
# PROMETHEUS METRICS
#
# WHY two sets of gauges:
#   predicted_* = raw LSTM output (what the model thinks)
#   safe_*      = max(prediction, p95 baseline)
#
#   Keeping both lets Grafana show:
#     - How much the safety guard is adding on top
#     - Whether the model is learning to match the baseline
# -------------------------------

PREDICTED_CPU = Gauge(
    "predicted_cpu_usage",
    "Predicted CPU usage (cores)"
)

PREDICTED_MEMORY = Gauge(
    "predicted_memory_usage",
    "Predicted memory usage (bytes)"
)

SAFE_CPU = Gauge(
    "safe_cpu_usage",
    "Safety-adjusted CPU usage (cores) — max(prediction, p95)"
)

SAFE_MEMORY = Gauge(
    "safe_memory_usage",
    "Safety-adjusted memory usage (bytes) — max(prediction, p95)"
)


class Aggregator:
    def __init__(self):
        self.prom = PrometheusClient()
        self.builder = FeatureBuilder()

        self.buffer = []  # sliding window

        self.trainer = OnlineTrainer()  # LSTM trainer

        # -------------------------------
        # CPU GAP FIX
        # -------------------------------
        self.last_valid_cpu = None

    def collect_metrics(self):
        data = self.prom.get_metrics()

        request_rate = data["request_rate"]
        cpu_usage = data["cpu_usage"]
        memory_usage = data["memory_usage"]

        # -------------------------------
        # CPU GAP FIX
        #
        # WHY: Prometheus sometimes returns 0.0 for CPU between
        # scrape intervals. Using the last known value avoids
        # feeding the LSTM a false zero that distorts training.
        # -------------------------------
        if cpu_usage == 0.0:
            if self.last_valid_cpu is not None:
                print("⚠️  CPU gap detected, using last valid value")
                cpu_usage = self.last_valid_cpu
            else:
                cpu_usage = 0.01
        else:
            self.last_valid_cpu = cpu_usage

        return request_rate, cpu_usage, memory_usage

    def update_buffer(self, feature):
        """
        Maintain fixed-size sliding window.
        WHY pop(0): We want the most recent WINDOW_SIZE steps,
        dropping the oldest entry as new data arrives.
        """
        self.buffer.append(feature)

        if len(self.buffer) > WINDOW_SIZE:
            self.buffer.pop(0)

    def get_sequence(self):
        """
        Convert buffer → LSTM input format.
        Shape: (WINDOW_SIZE, num_features)

        WHY return None if buffer not full:
        The LSTM needs exactly WINDOW_SIZE steps to make a
        meaningful prediction. Partial sequences would produce
        garbage output.
        """

        if len(self.buffer) < WINDOW_SIZE:
            return None

        sequence = []

        for f in self.buffer:
            sequence.append([
                f["request_rate"],
                f["cpu_usage"],
                f["memory_usage"],
                f["cpu_demand"],
                f["memory_demand"],
                f["heavy_ratio"]
            ])

        return np.array(sequence, dtype=np.float32)

    def run(self):
        print("🚀 Aggregator + LSTM + Safety Guard + YAML Generator started...")

        while True:
            try:
                # Step 1: Collect real-time metrics
                request_rate, cpu_usage, memory_usage = self.collect_metrics()

                # Step 2: Build feature vector
                feature = self.builder.build_feature_vector(
                    request_rate,
                    cpu_usage,
                    memory_usage
                )

                # Step 3: Update sliding window buffer
                self.update_buffer(feature)

                # Step 4: Build sequence for LSTM
                sequence = self.get_sequence()

                print("📊 Feature:", feature)

                # Step 5: ML Training + Prediction + Safety Guard + YAML
                if sequence is not None:
                    print("🧠 Sequence shape:", sequence.shape)

                    # Build training sample
                    x, y = build_sample(sequence)

                    # Train model on latest sample
                    loss, pred = self.trainer.train_step(x, y)

                    # Format raw LSTM output
                    pred_dict = format_prediction(pred)

                    print("📉 Loss:", loss)
                    print("🔮 Prediction:", pred_dict)

                    # ----------------------------------
                    # SAFETY GUARD LAYER (Phase 6)
                    #
                    # WHY max() and not just p95:
                    #   When the model predicts ABOVE p95 (spike
                    #   detected), we trust the model. When it
                    #   underpredicts, p95 acts as the floor.
                    #
                    # WHY call p95 every tick:
                    #   p95 is a rolling 5m window — it shifts as
                    #   workload changes. Stale p95 is worse than
                    #   no safety guard at all.
                    # ----------------------------------
                    p95 = self.prom.get_p95_metrics()

                    cpu_safe = max(pred_dict["cpu_pred"], p95["cpu_p95"])
                    mem_safe = max(pred_dict["memory_pred"], p95["memory_p95"])

                    print("🛡️  P95 Baseline:", p95)
                    print("🛡️  Safe Prediction:", {
                        "cpu_safe": cpu_safe,
                        "memory_safe": mem_safe
                    })

                    # ----------------------------------
                    # EXPORT SAFE VALUES TO PROMETHEUS
                    # ----------------------------------

                    # Raw model predictions (kept for Grafana comparison)
                    PREDICTED_CPU.set(pred_dict["cpu_pred"])
                    PREDICTED_MEMORY.set(pred_dict["memory_pred"])

                    # Safety-adjusted final recommendations
                    SAFE_CPU.set(cpu_safe)
                    SAFE_MEMORY.set(mem_safe)

                    # ----------------------------------
                    # YAML GENERATOR
                    #
                    # WHY after Prometheus export:
                    #   Metrics must be published first — if YAML
                    #   generation crashes for any reason, at least
                    #   Prometheus still has the latest safe values.
                    #
                    # WHY every tick:
                    #   Workload changes continuously. A YAML spec
                    #   generated once at startup would go stale.
                    #   In Phase 8+ we'll only write to disk when
                    #   the values change beyond a threshold.
                    # ----------------------------------
                    generate_resources_yaml(cpu_safe, mem_safe)

                time.sleep(QUERY_INTERVAL)

            except Exception as e:
                print(f"[ERROR] Aggregator loop failed: {e}")
                time.sleep(QUERY_INTERVAL)


# -------------------------------
# ENTRY POINT
# -------------------------------
if __name__ == "__main__":
    # Start Prometheus metrics server on port 8001
    start_http_server(8001)

    print("📡 Prometheus metrics available at http://localhost:8001/metrics")

    agg = Aggregator()
    agg.run()
