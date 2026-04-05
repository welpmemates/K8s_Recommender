# Package inclusion
import sys
import os

# Add infra/ to Python path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))


import time
import numpy as np

from prometheus_client import PrometheusClient
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


class Aggregator:
    def __init__(self):
        self.prom = PrometheusClient()
        self.builder = FeatureBuilder()

        self.buffer = []  # sliding window

        self.trainer = OnlineTrainer() # LSTM trainer

    def collect_metrics(self):
        request_rate = self.prom.get_metric(REQUEST_RATE_QUERY)
        cpu_usage = self.prom.get_metric(CPU_USAGE_QUERY)
        memory_usage = self.prom.get_metric(MEMORY_USAGE_QUERY)

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
        print("🚀 Aggregator + LSTM started...")

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

                # Step 5: Debug feature
                print("📊 Feature:", feature)

                # Step 6: ML Training + Prediction
                if sequence is not None:
                    print("🧠 Sequence shape:", sequence.shape)

                    # Build training sample
                    x, y = build_sample(sequence)

                    # Train model (online)
                    loss, pred = self.trainer.train_step(x, y)

                    # Format prediction
                    pred_dict = format_prediction(pred)

                    print("📉 Loss:", loss)
                    print("🔮 Prediction:", pred_dict)

                # Step 7: Sleep
                time.sleep(QUERY_INTERVAL)

            except Exception as e:
                print(f"[ERROR] Aggregator loop failed: {e}")
                time.sleep(QUERY_INTERVAL)


if __name__ == "__main__":
    agg = Aggregator()
    agg.run()
