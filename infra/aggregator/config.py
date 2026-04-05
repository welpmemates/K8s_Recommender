# Prometheus base URL
PROMETHEUS_URL = "http://prometheus-kube-prometheus-prometheus.monitoring.svc.cluster.local:9090"

# Query interval (seconds)
QUERY_INTERVAL = 15

# Kubernetes label selector
POD_REGEX = "mock-app.*"

# -------------------------------
# REAL-TIME METRICS
# -------------------------------

REQUEST_RATE_QUERY = 'irate(app_requests_total[15s])'

CPU_USAGE_QUERY = f'rate(container_cpu_usage_seconds_total{{pod=~"{POD_REGEX}"}}[30s])'

MEMORY_USAGE_QUERY = f'container_memory_usage_bytes{{pod=~"{POD_REGEX}"}}'


# -------------------------------
# SAFETY BASELINE (P95)
#
# WHY these queries:
#   - quantile_over_time operates on a range vector of SCALAR values
#   - We cannot wrap sum() inside quantile_over_time directly (invalid PromQL)
#   - Instead we apply quantile_over_time on the raw per-pod metric
#   - This gives us the 95th percentile of observed values over the last 5m
#   - Result = a single scalar safety floor per metric
# -------------------------------

CPU_P95_QUERY = f'''
quantile_over_time(
  0.95,
  rate(container_cpu_usage_seconds_total{{pod=~"{POD_REGEX}"}}[30s])[5m:]
)
'''

MEMORY_P95_QUERY = f'''
quantile_over_time(
  0.95,
  container_memory_usage_bytes{{pod=~"{POD_REGEX}"}}[5m:]
)
'''


# -------------------------------
# LSTM SETTINGS
# -------------------------------

WINDOW_SIZE = 10
