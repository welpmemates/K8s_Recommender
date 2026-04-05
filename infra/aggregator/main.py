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
# -------------------------------
PREDICTED_CPU = Gauge(
    "predicted_cpu_usage",
    "Predicted CPU usage (cores)"
)

PREDICTED_MEMORY = Gauge(
    "predicted_memory_usage",
    "Predicted memory usage (bytes)"
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
        request_rate = self.prom.get_metric(REQUEST_RATE_QUERY)
        cpu_usage = self.prom.get_metric(CPU_USAGE_QUERY)
        memory_usage = self.prom.get_metric(MEMORY_USAGE_QUERY)
        
        if cpu_usage == 0.0:
            if self.last_valid_cpu is not None:
                print("⚠️ CPU gap detected, using last value")
                cpu_usage = self.last_valid_cpu
            else:
                # fallback if no previous value
                cpu_usage = 0.01
        else:
            self.last_valid_cpu = cpu_usage

        return request_rate, cpu_usage, memory_usage

    def update_buffer(self, feature):
        """
        Maintain fixed-size sliding window
        """
        self.buffer.append(feature)

        if len(self.buffer) > WINDOW_SIZE:
            self.buffer.pop(0)

    def get_sequence(self):
        """
        Convert buffer → LSTM input format
        Shape: (WINDOW_SIZE, num_features)
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
        print("🚀 Aggregator + LSTM + Prometheus exporter started...")

        while True:
            try:
                # Step 1: Collect metrics
                request_rate, cpu_usage, memory_usage = self.collect_metrics()

                # Step 2: Build feature
                feature = self.builder.build_feature_vector(
                    request_rate,
                    cpu_usage,
                    memory_usage
                )

                # Step 3: Update buffer
                self.update_buffer(feature)

                # Step 4: Build sequence
                sequence = self.get_sequence()

                print("📊 Feature:", feature)

                # Step 5: ML Training + Prediction
                if sequence is not None:
                    print("🧠 Sequence shape:", sequence.shape)

                    # Build training sample
                    x, y = build_sample(sequence)

                    # Train model
                    loss, pred = self.trainer.train_step(x, y)

                    # Format prediction
                    pred_dict = format_prediction(pred)

                    print("📉 Loss:", loss)
                    print("🔮 Prediction:", pred_dict)

                    # -------------------------------
                    # UPDATE PROMETHEUS METRICS
                    # -------------------------------
                    PREDICTED_CPU.set(pred_dict["cpu_pred"])
                    PREDICTED_MEMORY.set(pred_dict["memory_pred"])

                time.sleep(QUERY_INTERVAL)

            except Exception as e:
                print(f"[ERROR] Aggregator loop failed: {e}")
                time.sleep(QUERY_INTERVAL)


# -------------------------------
# ENTRY POINT
# -------------------------------
if __name__ == "__main__":
    # Start Prometheus metrics server
    start_http_server(8001)

    print("📡 Prometheus metrics available at http://localhost:8001/metrics")

    agg = Aggregator()
    agg.run()
