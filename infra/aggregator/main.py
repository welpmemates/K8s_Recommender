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
# FOUR layers of CPU/memory metrics — each tells a different story:
#
#   predicted_*     → raw LSTM output (what the model learned)
#   safe_*          → max(prediction, p95)  (safety floor)
#   recommended_*   → safe * 1.2x buffer, converted to K8s units
#                     (what we'd actually put in a manifest)
#
# WHY expose recommended_* separately:
#   safe_* is in raw units (cores / bytes).
#   recommended_* is in K8s scheduling units (millicores / Mi).
#   Grafana panels showing "what K8s would get" should use
#   recommended_* — it's the actionable number.
# -------------------------------

PREDICTED_CPU = Gauge(
    "predicted_cpu_usage",
    "Predicted CPU usage (cores) — raw LSTM output"
)

PREDICTED_MEMORY = Gauge(
    "predicted_memory_usage",
    "Predicted memory usage (bytes) — raw LSTM output"
)

SAFE_CPU = Gauge(
    "safe_cpu_usage",
    "Safety-adjusted CPU usage (cores) — max(prediction, p95)"
)

SAFE_MEMORY = Gauge(
    "safe_memory_usage",
    "Safety-adjusted memory usage (bytes) — max(prediction, p95)"
)

RECOMMENDED_CPU = Gauge(
    "recommended_cpu_millicores",
    "Recommended CPU for K8s manifest (millicores) — safe * 1.2x buffer"
)

RECOMMENDED_MEMORY = Gauge(
    "recommended_memory_mebibytes",
    "Recommended memory for K8s manifest (MiB) — safe * 1.2x buffer"
)

class Aggregator:
    def __init__(self):
        self.prom    = PrometheusClient()
        self.builder = FeatureBuilder()
        self.buffer  = []         # sliding window
        self.trainer = OnlineTrainer()

        # CPU gap fix — last known good value
        self.last_valid_cpu = None

    def collect_metrics(self):
        data = self.prom.get_metrics()

        request_rate = data["request_rate"]
        cpu_usage    = data["cpu_usage"]
        memory_usage = data["memory_usage"]

        # -------------------------------
        # CPU GAP FIX
        # Prometheus occasionally returns 0.0 between scrape
        # intervals. Feeding that zero into LSTM distorts training.
        # Use last known value instead. Floor at 0.01 on cold start.
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
        pop(0) drops the oldest entry as new data arrives.
        """
        self.buffer.append(feature)
        if len(self.buffer) > WINDOW_SIZE:
            self.buffer.pop(0)

    def get_sequence(self):
        """
        Convert buffer → LSTM input tensor.
        Shape: (WINDOW_SIZE, num_features)
        Returns None until buffer is full — partial sequences
        produce garbage predictions.
        """
        if len(self.buffer) < WINDOW_SIZE:
            return None

        sequence = [
            [
                f["request_rate"],
                f["cpu_usage"],
                f["memory_usage"],
                f["cpu_demand"],
                f["memory_demand"],
                f["heavy_ratio"]
            ]
            for f in self.buffer
        ]

        return np.array(sequence, dtype=np.float32)

    def run(self):
        print("🚀 Aggregator + LSTM + Safety Guard + YAML Generator started...")

        while True:
            try:
                # ── Step 1: Real-time metrics ──────────────────────────
                request_rate, cpu_usage, memory_usage = self.collect_metrics()

                # ── Step 2: Feature vector ─────────────────────────────
                feature = self.builder.build_feature_vector(
                    request_rate, cpu_usage, memory_usage
                )

                # ── Step 3: Sliding window ─────────────────────────────
                self.update_buffer(feature)

                # ── Step 4: Build LSTM sequence ────────────────────────
                sequence = self.get_sequence()

                print("📊 Feature:", feature)

                if sequence is not None:
                    print("🧠 Sequence shape:", sequence.shape)

                    # ── Step 5: Train + predict ────────────────────────
                    x, y      = build_sample(sequence)
                    loss, pred = self.trainer.train_step(x, y)
                    pred_dict  = format_prediction(pred)

                    print("📉 Loss:", loss)
                    print("🔮 Prediction:", pred_dict)

                    # ── Step 6: Safety Guard (Phase 6) ─────────────────
                    # p95 is a rolling 5m window — fetch every tick so
                    # the floor tracks actual workload changes.
                    p95 = self.prom.get_p95_metrics()

                    cpu_safe = max(pred_dict["cpu_pred"],    p95["cpu_p95"])
                    mem_safe = max(pred_dict["memory_pred"], p95["memory_p95"])

                    print("🛡️  P95 Baseline:", p95)
                    print("🛡️  Safe Prediction:", {
                        "cpu_safe": cpu_safe,
                        "memory_safe": mem_safe
                    })

                    # ── Step 7: Export raw + safe to Prometheus ─────────
                    PREDICTED_CPU.set(pred_dict["cpu_pred"])
                    PREDICTED_MEMORY.set(pred_dict["memory_pred"])
                    SAFE_CPU.set(cpu_safe)
                    SAFE_MEMORY.set(mem_safe)

                    # ── Step 8: YAML Generator ───────────
                    # generate_resources_yaml now returns a dict with:
                    #   "cpu_requests_m"     → millicores
                    #   "memory_requests_mi" → MiB
                    # Internally it handles change detection + file write.
                    #
                    # WHY call AFTER Prometheus export:
                    #   If file write fails, metrics are already published.
                    #   Never let persistence block observability.
                    result = generate_resources_yaml(cpu_safe, mem_safe)

                    # ── Step 9: Export recommended values to Prometheus ─
                    # These are the K8s-unit values (millicores / Mi)
                    # that would go into an actual manifest — the most
                    # actionable numbers in the whole pipeline.
                    RECOMMENDED_CPU.set(result["cpu_requests_m"])
                    RECOMMENDED_MEMORY.set(result["memory_requests_mi"])

                    print(f"📡 Recommended → "
                          f"CPU: {result['cpu_requests_m']}m  "
                          f"Memory: {result['memory_requests_mi']}Mi")

                time.sleep(QUERY_INTERVAL)

            except Exception as e:
                print(f"[ERROR] Aggregator loop failed: {e}")
                time.sleep(QUERY_INTERVAL)


# -------------------------------
# ENTRY POINT
# -------------------------------
if __name__ == "__main__":
    start_http_server(8001)
    print("📡 Prometheus metrics available at http://localhost:8001/metrics")

    agg = Aggregator()
    agg.run()
