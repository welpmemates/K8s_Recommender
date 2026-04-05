# Prometheus base URL
PROMETHEUS_URL = "http://localhost:9090"

# Query interval (seconds)
QUERY_INTERVAL = 15

# Kubernetes label selector
POD_REGEX = "mock-app.*"

# Prometheus Queries
REQUEST_RATE_QUERY = 'irate(app_requests_total[15s])'

CPU_USAGE_QUERY = f'rate(container_cpu_usage_seconds_total{{pod=~"{POD_REGEX}"}}[30s])'

MEMORY_USAGE_QUERY = f'container_memory_usage_bytes{{pod=~"{POD_REGEX}"}}'

# Sliding window size for LSTM
WINDOW_SIZE = 10
