from fastapi import FastAPI
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from fastapi.responses import Response
import time
import random
import hashlib
import uuid

app = FastAPI()

# -------------------------------
# GLOBAL STATE
# -------------------------------
MEMORY_HOG = []
TOKEN_STATS = {}

# -------------------------------
# PROMETHEUS METRICS
# -------------------------------
REQUEST_COUNT = Counter(
    "app_requests_total",
    "Total number of requests"
)

REQUEST_DURATION = Histogram(
    "app_request_duration_seconds",
    "Request duration"
)

TOKEN_CPU_ESTIMATE = Gauge(
    "token_cpu_estimate",
    "Estimated CPU cost per token"
)

TOKEN_MEMORY_ESTIMATE = Gauge(
    "token_memory_estimate",
    "Estimated memory cost per token"
)

ACTIVE_TOKENS = Gauge(
    "active_tokens",
    "Number of active tokens"
)

# -------------------------------
# TOKEN GENERATOR
# -------------------------------
def generate_token():
    return str(uuid.uuid4())

# -------------------------------
# WORKLOAD ENDPOINT
# -------------------------------
@app.get("/work")
def do_work(size: int=1000, sleep: float=0.01, retain: bool=False):
    start = time.time()
    token = generate_token()

    data = []

    for _ in range(size):
        s = str(random.random()).encode()
        hashlib.sha256(s).hexdigest()
        data.append(s)

    if retain:
        MEMORY_HOG.append(data)

    time.sleep(sleep)

    duration = time.time() - start

    # -------------------------------
    # Estimate resource behavior
    # -------------------------------
    cpu_estimate = size * 0.00001
    mem_estimate = size * 0.0005

    TOKEN_STATS[token] = {
        "cpu": cpu_estimate,
        "memory": mem_estimate,
        "duration": duration
    }

    # -------------------------------
    # Update Prometheus metrics
    # -------------------------------
    REQUEST_COUNT.inc()
    REQUEST_DURATION.observe(duration)

    TOKEN_CPU_ESTIMATE.set(cpu_estimate)
    TOKEN_MEMORY_ESTIMATE.set(mem_estimate)

    ACTIVE_TOKENS.set(len(TOKEN_STATS))

    return {
        "token": token,
        "items": size,
        "duration": duration,
        "retained_chunks": len(MEMORY_HOG)
    }

# -------------------------------
# METRICS ENDPOINT
# -------------------------------
@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type="text/plain")