# Package inclusion
import sys
import os

# Add infra/ to Python path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import time
import math
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


# ================================================================
# PROMETHEUS METRICS
#
# We now have FOUR layers of metrics:
#
#  Layer 1 — Raw prediction
#   predicted_cpu_usage        cores
#   predicted_memory_usage     bytes
#
#  Layer 2 — Safety-adjusted
#   safe_cpu_usage             cores
#   safe_memory_usage          bytes
#
#  Layer 3 — K8s manifest units
#   recommended_cpu_millicores millicores
#   recommended_memory_mebibytes MiB
#
#  Layer 4 — Evaluation (NEW in Phase 9)
#   cpu_absolute_error         |actual - predicted| in cores
#   memory_absolute_error      |actual - predicted| in bytes
#   cpu_mae                    rolling mean absolute error
#   memory_mae                 rolling mean absolute error
#   cpu_rmse                   rolling root mean squared error
#   memory_rmse                rolling root mean squared error
#   cpu_spike_miss             1 if actual > predicted * 1.5
#   memory_spike_miss          1 if actual > predicted * 1.5
#
# WHY keep all layers:
#   Each layer answers a different question in Grafana:
#   "What did the model think?" vs "What's safe?" vs
#   "What goes in the manifest?" vs "How wrong was it?"
# ================================================================

# -- Layer 1: Raw prediction --
PREDICTED_CPU = Gauge(
    "predicted_cpu_usage",
    "Predicted CPU usage (cores) — raw LSTM output"
)
PREDICTED_MEMORY = Gauge(
    "predicted_memory_usage",
    "Predicted memory usage (bytes) — raw LSTM output"
)

# -- Layer 2: Safety-adjusted --
SAFE_CPU = Gauge(
    "safe_cpu_usage",
    "Safety-adjusted CPU usage (cores) — max(prediction, p95)"
)
SAFE_MEMORY = Gauge(
    "safe_memory_usage",
    "Safety-adjusted memory usage (bytes) — max(prediction, p95)"
)

# -- Layer 3: K8s manifest units --
RECOMMENDED_CPU = Gauge(
    "recommended_cpu_millicores",
    "Recommended CPU for K8s manifest (millicores)"
)
RECOMMENDED_MEMORY = Gauge(
    "recommended_memory_mebibytes",
    "Recommended memory for K8s manifest (MiB)"
)

# -- Layer 4: Evaluation metrics (Phase 9) --

CPU_ABS_ERROR = Gauge(
    "cpu_absolute_error",
    "Absolute CPU prediction error this tick (cores) = |actual - predicted|"
)
MEMORY_ABS_ERROR = Gauge(
    "memory_absolute_error",
    "Absolute memory prediction error this tick (bytes) = |actual - predicted|"
)

CPU_MAE = Gauge(
    "cpu_mae",
    "Rolling Mean Absolute Error for CPU over last WINDOW_SIZE predictions"
)
MEMORY_MAE = Gauge(
    "memory_mae",
    "Rolling Mean Absolute Error for memory over last WINDOW_SIZE predictions"
)

CPU_RMSE = Gauge(
    "cpu_rmse",
    "Rolling Root Mean Squared Error for CPU over last WINDOW_SIZE predictions"
)
MEMORY_RMSE = Gauge(
    "memory_rmse",
    "Rolling Root Mean Squared Error for memory over last WINDOW_SIZE predictions"
)

CPU_SPIKE_MISS = Gauge(
    "cpu_spike_miss",
    "1 if actual CPU > predicted * 1.5 (model missed a spike), else 0"
)
MEMORY_SPIKE_MISS = Gauge(
    "memory_spike_miss",
    "1 if actual memory > predicted * 1.5 (model missed a spike), else 0"
)

class Aggregator:
    def __init__(self):
        self.prom    = PrometheusClient()
        self.builder = FeatureBuilder()
        self.buffer  = []
        self.trainer = OnlineTrainer()

        # CPU gap fix
        self.last_valid_cpu = None

        # --------------------------------------------------
        # EVALUATION BUFFERS (Phase 9)
        #
        # WHY separate buffers from the feature buffer:
        #   The feature buffer holds raw sensor readings used
        #   to build LSTM input sequences.
        #   The error buffers hold PREDICTION ERRORS — they only
        #   get a value after we have both a prediction AND the
        #   corresponding actual reading from the same tick.
        #   Mixing them would corrupt the LSTM input.
        #
        # WHY same WINDOW_SIZE:
        #   Consistency. MAE/RMSE over 10 steps = same time
        #   horizon as the LSTM looks back. Makes the metrics
        #   directly comparable to model loss.
        # --------------------------------------------------
        self.error_buffer_cpu    = []
        self.error_buffer_memory = []

    # ----------------------------------------------------------
    # METRIC COLLECTION
    # ----------------------------------------------------------

    def collect_metrics(self):
        data = self.prom.get_metrics()

        request_rate = data["request_rate"]
        cpu_usage    = data["cpu_usage"]
        memory_usage = data["memory_usage"]

        # CPU gap fix — Prometheus occasionally returns 0.0
        # between scrape intervals. Using last known value
        # prevents feeding the LSTM a false zero.
        if cpu_usage == 0.0:
            if self.last_valid_cpu is not None:
                print("⚠️  CPU gap detected, using last valid value")
                cpu_usage = self.last_valid_cpu
            else:
                cpu_usage = 0.01
        else:
            self.last_valid_cpu = cpu_usage

        return request_rate, cpu_usage, memory_usage

    # ----------------------------------------------------------
    # SLIDING WINDOW
    # ----------------------------------------------------------

    def update_buffer(self, feature):
        self.buffer.append(feature)
        if len(self.buffer) > WINDOW_SIZE:
            self.buffer.pop(0)

    def get_sequence(self):
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

    # ----------------------------------------------------------
    # EVALUATION HELPERS (Phase 9)
    # ----------------------------------------------------------

    def _update_error_buffer(self, cpu_error: float, mem_error: float):
        """
        Append signed errors and keep buffer at WINDOW_SIZE.

        WHY signed (not abs) in the buffer:
          We store signed errors so we can detect systematic
          bias (always over or always under-predicting).
          abs() is applied only when computing MAE.
          RMSE squares them anyway so sign doesn't matter there.
        """
        self.error_buffer_cpu.append(cpu_error)
        self.error_buffer_memory.append(mem_error)

        if len(self.error_buffer_cpu) > WINDOW_SIZE:
            self.error_buffer_cpu.pop(0)
        if len(self.error_buffer_memory) > WINDOW_SIZE:
            self.error_buffer_memory.pop(0)

    def _compute_mae(self, error_buffer: list) -> float:
        """
        MAE = mean of absolute errors in buffer.

        WHY MAE and not just loss:
          LSTM loss is on normalised values — uninterpretable
          to a human. MAE here is in real units (cores / bytes)
          so you can directly ask: "is 0.002 cores error bad?"
        """
        if not error_buffer:
            return 0.0
        return float(np.mean(np.abs(error_buffer)))

    def _compute_rmse(self, error_buffer: list) -> float:
        """
        RMSE = sqrt(mean of squared errors).

        WHY RMSE in addition to MAE:
          RMSE penalises large errors more than MAE does.
          A system that occasionally misses badly will show
          RMSE >> MAE. If RMSE ≈ MAE the errors are consistent.
        """
        if not error_buffer:
            return 0.0
        return float(math.sqrt(np.mean(np.square(error_buffer))))

    def _detect_spike_miss(self, actual: float, predicted: float) -> int:
        """
        Returns 1 if the model dangerously under-predicted.

        WHY 1.5x threshold:
          If actual load is 50% higher than predicted, the pod
          is severely under-provisioned. At that point K8s will
          either throttle CPU or OOMKill the pod.
          1.5x is the industry-standard "danger zone" threshold.

        WHY not just (actual > predicted):
          Small over-runs happen all the time and are handled by
          the p95 safety guard. We only care about LARGE misses
          that the safety guard itself can't absorb.

        Edge case — predicted is 0 or negative:
          Guard against division-by-zero / nonsense comparisons.
        """
        if predicted <= 0:
            return 0
        return 1 if actual > predicted * 1.5 else 0

    def _run_evaluation(
        self,
        cpu_actual:   float,
        mem_actual:   float,
        cpu_pred:     float,
        mem_pred:     float
    ):
        """
        Compute all evaluation metrics and export to Prometheus.

        Called every tick after we have both a prediction and
        the actual reading from the same timestep.

        Args:
            cpu_actual  — real CPU reading this tick (cores)
            mem_actual  — real memory reading this tick (bytes)
            cpu_pred    — raw LSTM CPU prediction (cores)
            mem_pred    — raw LSTM memory prediction (bytes)
        """

        # 1. Per-tick signed errors
        cpu_error = cpu_actual - cpu_pred
        mem_error = mem_actual - mem_pred

        # 2. Per-tick absolute errors (what we show on the gauge)
        cpu_abs_err = abs(cpu_error)
        mem_abs_err = abs(mem_error)

        # 3. Update rolling error buffers
        self._update_error_buffer(cpu_error, mem_error)

        # 4. Rolling MAE + RMSE
        cpu_mae  = self._compute_mae(self.error_buffer_cpu)
        mem_mae  = self._compute_mae(self.error_buffer_memory)
        cpu_rmse = self._compute_rmse(self.error_buffer_cpu)
        mem_rmse = self._compute_rmse(self.error_buffer_memory)

        # 5. Spike miss detection
        cpu_spike  = self._detect_spike_miss(cpu_actual, cpu_pred)
        mem_spike  = self._detect_spike_miss(mem_actual, mem_pred)

        # 6. Log evaluation summary
        print(f"📐 Evaluation │ "
              f"cpu_err={cpu_error:+.6f}  mem_err={mem_error:+.0f}B")
        print(f"   MAE  │ cpu={cpu_mae:.6f}  mem={mem_mae:.0f}B")
        print(f"   RMSE │ cpu={cpu_rmse:.6f}  mem={mem_rmse:.0f}B")
        if cpu_spike:
            print("🚨 CPU SPIKE MISS — actual > predicted * 1.5!")
        if mem_spike:
            print("🚨 MEMORY SPIKE MISS — actual > predicted * 1.5!")

        # 7. Export all evaluation metrics to Prometheus
        CPU_ABS_ERROR.set(cpu_abs_err)
        MEMORY_ABS_ERROR.set(mem_abs_err)
        CPU_MAE.set(cpu_mae)
        MEMORY_MAE.set(mem_mae)
        CPU_RMSE.set(cpu_rmse)
        MEMORY_RMSE.set(mem_rmse)
        CPU_SPIKE_MISS.set(cpu_spike)
        MEMORY_SPIKE_MISS.set(mem_spike)

    # ----------------------------------------------------------
    # MAIN LOOP
    # ----------------------------------------------------------

    def run(self):
        print("🚀 Aggregator + LSTM + Safety Guard + YAML + Evaluation started...")
        while True:
            try:
                # ── Step 1: Collect real-time metrics ─────────────────
                request_rate, cpu_usage, memory_usage = self.collect_metrics()

                # ── Step 2: Build feature vector ──────────────────────
                feature = self.builder.build_feature_vector(
                    request_rate, cpu_usage, memory_usage
                )

                # ── Step 3: Sliding window ────────────────────────────
                self.update_buffer(feature)

                # ── Step 4: Build LSTM sequence ───────────────────────
                sequence = self.get_sequence()

                print("📊 Feature:", feature)

                if sequence is not None:
                    print("🧠 Sequence shape:", sequence.shape)

                    # ── Step 5: Train + predict ────────────────────────
                    x, y       = build_sample(sequence)
                    loss, pred = self.trainer.train_step(x, y)
                    pred_dict  = format_prediction(pred)

                    print("📉 Loss:", loss)
                    print("🔮 Prediction:", pred_dict)

                    # ── Step 6: Safety Guard ───────────────────────────
                    p95 = self.prom.get_p95_metrics()

                    cpu_safe = max(pred_dict["cpu_pred"],    p95["cpu_p95"])
                    mem_safe = max(pred_dict["memory_pred"], p95["memory_p95"])

                    print("🛡️  P95 Baseline:", p95)
                    print("🛡️  Safe Prediction:", {
                        "cpu_safe": cpu_safe,
                        "memory_safe": mem_safe
                    })

                    # ── Step 7: Export raw + safe to Prometheus ────────
                    PREDICTED_CPU.set(pred_dict["cpu_pred"])
                    PREDICTED_MEMORY.set(pred_dict["memory_pred"])
                    SAFE_CPU.set(cpu_safe)
                    SAFE_MEMORY.set(mem_safe)

                    # ── Step 8: YAML Generator ─────────────────────────
                    result = generate_resources_yaml(cpu_safe, mem_safe)

                    RECOMMENDED_CPU.set(result["cpu_requests_m"])
                    RECOMMENDED_MEMORY.set(result["memory_requests_mi"])

                    print(f"📡 Recommended → "
                          f"CPU: {result['cpu_requests_m']}m  "
                          f"Memory: {result['memory_requests_mi']}Mi")

                    # ── Step 9: Evaluation Layer (Phase 9) ────────────
                    #
                    # WHY use cpu_usage / memory_usage as "actual":
                    #   These are the real readings from THIS tick —
                    #   the same timestep the prediction was made for.
                    #   Comparing prediction[t] vs actual[t] is the
                    #   standard supervised evaluation protocol.
                    #
                    # WHY do evaluation AFTER YAML export:
                    #   Evaluation is read-only — it never changes the
                    #   pipeline output. Always put it last so a bug
                    #   here can't corrupt predictions or YAML output.
                    self._run_evaluation(
                        cpu_actual = cpu_usage,
                        mem_actual = memory_usage,
                        cpu_pred   = pred_dict["cpu_pred"],
                        mem_pred   = pred_dict["memory_pred"]
                    )

                time.sleep(QUERY_INTERVAL)

            except Exception as e:
                print(f"[ERROR] Aggregator loop failed: {e}")
                time.sleep(QUERY_INTERVAL)


# ================================================================
# ENTRY POINT
# ================================================================
if __name__ == "__main__":
    start_http_server(8001)
    print("📡 Prometheus metrics available at http://localhost:8001/metrics")

    agg = Aggregator()
    agg.run()
