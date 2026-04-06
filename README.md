# 🚀 K8s Resource Recommender

Online Learning-Based Kubernetes Resource Recommendation System using tokenized request behavior and LSTM.

This project builds a system that:

* Runs dynamic workloads inside Kubernetes
* Observes real-time CPU & memory usage
* Converts request patterns into structured features
* Trains an online LSTM model
* Recommends optimal Kubernetes resource configurations

---

# 🧠 System Overview

Instead of directly modeling requests, we use a **token abstraction layer**:

```
Request → Token → Resource Signature → Aggregated Features → LSTM
```

### 🔑 Key Idea

* Tokens are **unbounded**
* We convert them into **fixed-size time-series features**
* These features are used for **online learning**

---

# 🧱 Project Structure

```
K8S_RECOMMENDER/
├── mock_app/
│   ├── app/                # FastAPI application
│   |    ├── main.py
│   ├── docker/             # Dockerfile
│   |    ├── Dockerfile
│   ├── k8s/                # Kubernetes manifests
│   |    ├── deployment.yaml
│   |    ├── service.yaml
│   |    ├── servicemonitor.yaml
│   ├── locust/             # Load testing scripts
│   |    ├── locustfile.py
├── infra/                  # ML + aggregation services
│   ├── aggregator/
│   |    ├── config.py
│   |    ├── feature_builder.py
│   |    ├── main.py
│   |    ├── prometheus_client.py
│   |    ├── deployment.yaml
│   |    ├── service.yaml
│   |    ├── servicemonitor.yaml
│   |    ├── Dockerfile
│   ├── grafana/
│   |    ├── dashboard.json
│   ├── ml/
│   |    ├── config.py
│   |    ├── dataset.py
│   |    ├── model.py
│   |    ├── trainer.py
│   |    ├── utils.py
├── README.md
└── requirements.txt
```

---

# 🔧 Environment Setup

## 1. Install Base Dependencies

```bash
sudo apt update
sudo apt upgrade -y

sudo apt install -y curl wget git build-essential \
ca-certificates software-properties-common docker.io
```

## Verify Installations

```bash
apt --version
curl --version
git --version
gcc --version
```

---

# 🐳 Docker Setup

```bash
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker $USER
newgrp docker
```

## Verify Docker

```bash
docker --version
docker run hello-world
```

---

# ☸️ Kubernetes Setup

## Install kubectl

```bash
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install kubectl /usr/local/bin/kubectl
kubectl version --client
```

## Install Minikube

```bash
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube
minikube version
```

## Start Cluster

```bash
minikube start --driver=docker
kubectl get nodes
```

---

# ⚙️ Helm Setup

```bash
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
helm version
```

---

# 🐍 Python Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

## Install Dependencies

```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install numpy pandas scikit-learn
pip install prometheus-client requests pyyaml matplotlib
pip install fastapi uvicorn locust
```

## Verify Setup

```bash
python - <<EOF
import torch, numpy, pandas, sklearn
import prometheus_client, yaml, matplotlib

print("All imports OK")
print("Torch version:", torch.__version__)
EOF
```

---

# 🚀 Phase 1 — Workload + Token System

## Start Kubernetes

```bash
minikube start
minikube addons enable metrics-server
```

## Build Docker Image

```bash
eval $(minikube docker-env)
docker build -t mock-fastapi:latest -f mock_app/docker/Dockerfile mock_app
```

## Deploy Application

```bash
kubectl apply -f mock_app/k8s/
kubectl get pods
```

## Test Application

```bash
minikube ip
curl "http://<ip>:30007/work?size=10000"
```

## Metrics Endpoint

```
http://<ip>:30007/metrics
```

---

## Observe Resource Usage

```bash
kubectl top pods
```

---

## Load Testing (Locust)

```bash
cd mock_app/locust
locust --host=http://<ip>:30007
```

Open:

```
http://localhost:8089
```

---

# 📊 Phase 2 — Prometheus + Grafana

## Create Monitoring Namespace

```bash
kubectl create namespace monitoring
```

---

## Install Monitoring Stack

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring
```

---

## Verify Monitoring Pods

```bash
kubectl get pods -n monitoring
```

---

## Access Prometheus

```bash
kubectl port-forward -n monitoring svc/prometheus-kube-prometheus-prometheus 9090:9090
```

Open:

```
http://localhost:9090
```

---

## Access Grafana

```bash
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80
```

Open:

```
http://localhost:3000
```

---

## 🔐 Grafana Login

Get password:

```bash
kubectl --namespace monitoring get secrets prometheus-grafana \
  -o jsonpath="{.data.admin-password}" | base64 -d ; echo
```

Login:

```
Username: admin
Password: <output of above command>
```

---

# 📈 Dashboard Panels

Your Grafana dashboard includes:

1. **Total Requests** (Stat)
2. **Request Rate (req/sec)** (Time Series)
3. **CPU Usage (cores)** (Gauge)
4. **Memory Usage (MB)** (Bar Gauge)

---

# 🤝 Grafana Dashboard

---

## Import on another system

```
Grafana → Dashboards → Import → Upload JSON
```

---

# 🚀 Phase 3 — Feature Aggregation (COMPLETED)

## 🎯 Objective

Convert raw Prometheus time-series metrics into structured, fixed-size feature vectors suitable for training an online LSTM model.

---

## 🧠 Key Concept

Prometheus Metrics → Aggregation → Sliding Window → LSTM Input

Instead of feeding raw requests or tokens directly into the model, we transform system behavior into time-based feature vectors. This converts unbounded request streams into bounded, learnable sequences.

---

## ⚙️ Components Implemented

### 1. Prometheus Client

- Queries Prometheus HTTP API (`/api/v1/query`)
- Extracts numeric values from responses
- Aggregates metrics across all pods
- Supports:
  - Request rate
  - CPU usage
  - Memory usage

---

### 2. Feature Builder

At each timestep, builds a structured feature vector:

{
  timestamp,
  request_rate,
  cpu_usage,
  memory_usage,
  cpu_demand,
  memory_demand,
  heavy_ratio
}

Derived features:

- CPU Demand → estimated from request rate  
- Memory Demand → estimated from request rate  
- Heavy Ratio → represents workload complexity  

---

### 3. Aggregator Loop

- Runs every 15 seconds
- Continuously performs:

Collect Metrics → Build Features → Store → Repeat

- Streams real-time system behavior

---

### 4. Sliding Window Buffer (CRITICAL)

- Maintains last 10 timesteps
- Converts feature stream into sequences

Final sequence shape:

(10, 6)

Where each timestep contains:

request_rate, cpu_usage, memory_usage, cpu_demand, memory_demand, heavy_ratio

---

## 🔁 Data Flow

Kubernetes Pods  
↓  
Prometheus Metrics  
↓  
Aggregator Service  
↓  
Feature Vectors  
↓  
Sliding Window Buffer  
↓  
LSTM-ready Sequences   

---

# 🚀 Phase 4 — Online LSTM Model (COMPLETED)

## 🎯 Objective

Train a real-time LSTM model that predicts future CPU and memory usage from aggregated time-series data.

---

## 🧠 Architecture
```bash
Sequence (10, 6) → LSTM → Prediction (CPU, Memory)
```

---

## ⚙️ Components

### 1. LSTM Model (PyTorch)

- Input: 6 features
- Hidden size: 64
- Output: 2 values (CPU, Memory)

### 2. Dataset Builder
```bash
Input:  (9, 6)
Target: (cpu_usage, memory_usage)
```

### 3. Online Training Loop

At every timestep:

1. Sequence generated
2. Sample built
3. Forward pass
4. Loss computed (MSE)
5. Backpropagation
6. Weights updated

### 4. Normalization (CRITICAL)

- Memory scaled (`÷ 1e8`)
- Demand scaled
- Prevents exploding gradients

---

## 🔁 Data Flow
```bash
Prometheus → Aggregator → Sequence → LSTM → Prediction → Update
```

---

## 📊 Output Example
```bash
cpu_pred:    0.48
memory_pred: 78000000
```

---

# 🚀 Phase 5 — Real-Time Prediction Observability (COMPLETED)

## 🎯 Objective

Expose LSTM predictions as Prometheus metrics and visualize them in Grafana alongside actual system usage.

This phase transforms the system into a **fully observable ML pipeline**.

---

## 🧠 Key Concept

```bash
Actual Metrics vs Predicted Metrics → Real-Time Comparison → Model Evaluation
```

We treat ML predictions as first-class observability signals.

### ⚙️ Components Implemented

1. Prometheus Exporter (Aggregator)

The aggregator now exposes:

predicted_cpu_usage
predicted_memory_usage

These are published via:
```bash
http://<aggregator>:8001/metrics
```

2. Kubernetes Integration

The aggregator is deployed inside Kubernetes:

Deployment → runs aggregator container
Service → exposes metrics
ServiceMonitor → enables Prometheus scraping

3. Prometheus Scraping

Prometheus automatically collects:

Actual system metrics (CPU, memory, requests)
Predicted metrics (from LSTM)

4. Grafana Dashboard

A comprehensive dashboard was built to visualize:

📊 Core Panels
CPU Usage: Actual vs LSTM Prediction
Memory Usage: Actual vs LSTM Prediction
CPU Prediction Error
Memory Prediction Error
Model Accuracy Indicator

📈 Key Queries
CPU (Actual vs Predicted)
rate(container_cpu_usage_seconds_total{pod=~"mock-app.*"}[30s])
predicted_cpu_usage
Memory (Actual vs Predicted)
container_memory_usage_bytes{pod=~"mock-app.*"}
predicted_memory_usage
Prediction Error (IMPORTANT)
abs(
  sum(rate(container_cpu_usage_seconds_total{pod=~"mock-app.*"}[30s]))
  - on() group_left()
  predicted_cpu_usage
)
abs(
  sum(container_memory_usage_bytes{pod=~"mock-app.*"})
  - on() group_left()
  predicted_memory_usage
)
Model Accuracy Indicator
1 - abs(
  sum(rate(container_cpu_usage_seconds_total{pod=~"mock-app.*"}[30s]))
  - on() group_left()
  predicted_cpu_usage
)

### 🧠 Important Insight (VERY IMPORTANT)

Prometheus requires label alignment for metric operations.

To compute prediction error:

Metrics must be aggregated first
Label mismatches must be handled using:
on() group_left()

This ensures correct many-to-one matching between:

Multiple pods (actual metrics)
Single prediction (model output)
```bash
🔁 Data Flow
Kubernetes Pods
↓
Prometheus Metrics
↓
Aggregator (Feature Builder + LSTM)
↓
Predicted Metrics Exported
↓
Prometheus Scrapes
↓
Grafana Visualizes
```

### 🚀 System Capability (AFTER PHASE 5)

The system now:

Observes workload behavior
Learns from real-time data
Predicts future resource usage
Visualizes predictions alongside actual metrics

⚠️ Notes
Predictions may initially lag or fluctuate
Model stabilizes with continuous training
Error metrics improve over time
Requires sustained load for meaningful learning

---

# 🚀 Phase 6 — Safety Guard (COMPLETED)
## 🎯 Objective

Prevent under-provisioning by introducing a statistical safety baseline using historical metrics.

This ensures that the system never recommends resources lower than what recent workload patterns demand.

## 🧠 Key Concept
Final Recommendation = max(Model Prediction, Safety Baseline)

Where:
Model Prediction → LSTM output
Safety Baseline → p95 (95th percentile) of recent usage

## ❗ Why This Is Critical

LSTM models:
May underpredict during sudden spikes
Learn with slight delay in dynamic systems

Without safety:
Underprediction → OOMKill → Pod Crash → SLA Violation

## ⚙️ Components Implemented
1. Safety Baseline (p95)

We compute a rolling 95th percentile over the last 5 minutes.

CPU
```bash
quantile_over_time(
  0.95,
  rate(container_cpu_usage_seconds_total{pod=~"mock-app.*"}[30s])[5m:]
)
```

```bash
Memory
quantile_over_time(
  0.95,
  container_memory_usage_bytes{pod=~"mock-app.*"}[5m:]
)
```

2. Prometheus Client Extension

Added:
```bash
get_p95_metrics()
```

Responsibilities:
Query Prometheus for p95 values
Safely extract values
Return defaults (0.0) if data missing

3. Safety Guard Logic
Inside the aggregator loop:

```bash
cpu_safe = max(cpu_pred, cpu_p95)
memory_safe = max(memory_pred, memory_p95)
```

4. New Prometheus Metrics
The system now exports:
```bash
safe_cpu_usage
safe_memory_usage
```
These represent final recommended values.

5. Observability
Logs now include:
```bash
🔮 Prediction: {...}
🛡️ P95 Baseline: {...}
🛡️ Safe Prediction: {...}
```
This makes system behavior fully transparent.

```bash
🔁 Updated Data Flow
Kubernetes Pods
↓
Prometheus Metrics
↓
Aggregator (Feature Builder + LSTM)
↓
Predicted Metrics
↓
Safety Guard (p95 baseline)
↓
Safe Metrics Exported
↓
Prometheus Scrapes
↓
Grafana Visualizes
```

## 📊 System Behavior
Scenario	Outcome
Prediction ≥ p95	Model trusted
Prediction < p95	Safety baseline applied
Missing p95 data	Falls back to prediction

---

# 🚀 Phase 7 — YAML Generator (COMPLETED)
## 🎯 Objective
Convert safe, model-driven predictions into real Kubernetes resource configurations.

This phase transforms the system from observational + predictive into an actionable decision system.

## 🧠 Key Concept
Safe Predictions → Resource Conversion → Kubernetes YAML
We take:
```bash
safe_cpu_usage (cores)
safe_memory_usage (bytes)
```

And convert them into:
```bash
resources:
  requests:
    cpu: 200m
    memory: 256Mi
  limits:
    cpu: 400m
    memory: 512Mi
❗ Why This Is Critical
```

Before Phase 7:
System observes metrics ✅
Model predicts usage ✅
Safety guard prevents underprediction ✅
BUT Kubernetes does not use these values ❌

After Phase 7:
AI → Safe Decision → Deployable Configuration
⚙️ Components Implemented
1. YAML Generator Module

📁 infra/aggregator/yaml_generator.py

Responsibilities:
Convert CPU → millicores
Convert memory → Mi (Mebibytes)
Apply safety buffer
Generate Kubernetes-compatible resource spec
Print YAML output

2. Unit Conversion (CRITICAL)
```bash
CPU:

cores → millicores
0.2 → 200m

Memory:

bytes → Mi
(÷ 1024²)
```

Why this matters:
Kubernetes does NOT accept raw floats
Uses strict resource units
Incorrect conversion = broken deployments

3. Safety Buffer Layer (Phase 7 Addition)
Even after p95 safety:
```bash
cpu_final    = safe_cpu    × 1.2
memory_final = safe_memory × 1.2
```

🧠 Why?
Handles sudden spikes beyond p95
Prevents throttling / OOMKill
Industry-standard overprovisioning

4. Requests & Limits Strategy
```bash
requests = buffered values
limits   = 2 × requests
```

Why:
Requests → scheduler guarantee
Limits → hard ceiling

Too low → OOMKill
Too high → wasted resources

5. Aggregator Integration
Inside: 📁 infra/aggregator/main.py

After safety guard: generate_resources_yaml(cpu_safe, mem_safe)

✔ Runs every cycle
✔ Uses real-time predictions
✔ Keeps system adaptive

```bash
🔁 Updated Data Flow
Kubernetes Pods
↓
Prometheus Metrics
↓
Aggregator (Feature Builder + LSTM)
↓
Predicted Metrics
↓
Safety Guard (p95 baseline)
↓
Safe Metrics
↓
YAML Generator ✅
↓
Kubernetes Resource Spec (READY)
```

## 🚀 System Capability (AFTER PHASE 7)

The system now:
Observes workload behavior
Learns from real-time data
Predicts future resource usage
Applies safety guarantees
Generates Kubernetes-ready configurations

---

# 🚀 Phase 8 — YAML Persistence + Change Detection (COMPLETED)

## 🎯 Objective

Persist generated Kubernetes resource configurations to disk and prevent unnecessary updates using intelligent change detection.

This phase upgrades the system from **generating recommendations** to **managing stable, production-ready outputs**.

---

## 🧠 Key Concept

```bash
Safe Predictions → Buffered Resources → YAML File → Change Detection → Stable Output

Instead of printing YAML every cycle, we now:

Persist recommendations to a file
Update ONLY when meaningful changes occur

❗ Why This Is Critical
Without Phase 8:

YAML would be rewritten every 15 seconds ❌
Future auto-apply systems would trigger continuous rolling updates ❌
System becomes unstable in real deployments ❌

With Phase 8:

Only significant workload changes trigger updates ✅
Prevents unnecessary restarts ✅
Makes system production-safe ✅
⚙️ Components Implemented
1. YAML File Persistence

📁 infra/aggregator/yaml_generator.py

The system now writes to:

/mnt/aggregator-output/generated_resources.yaml

This path is mapped via: Host → Minikube → Container

Example:
minikube mount ~/Documents/K8s_Recommender/infra/aggregator/generation:/mnt/aggregator-output

2. Change Detection (CRITICAL)

We only update the YAML if resource values change significantly:

CHANGE_THRESHOLD = 0.10   # 10%

Logic:

if relative_change > 10%:
    write YAML
else:
    skip update
🧠 Why Relative Change?

Absolute changes don’t scale:

5m CPU change is huge at low usage
Same 5m is negligible at high usage

Relative change ensures consistent sensitivity.

3. Module-Level State Tracking

We track previously written values:

_last_cpu_m
_last_mem_mi

Used to compare:

new vs previous values
4. Smart YAML Writing

On change:

✅ Print full YAML
✅ Write to file

On no change:

⏸️ Skip write (prevents churn)
5. Prometheus Integration (IMPORTANT)

Even when YAML is NOT rewritten:

The system still exports:

recommended_cpu_millicores
recommended_memory_mebibytes

This ensures:

Grafana always shows latest recommendations
Observability is never blocked by file writes

6. Resource Conversion Pipeline (FINAL FORM)
LSTM Prediction
        ↓
Safety Guard (p95)
        ↓
Safe Values
        ↓
+20% Buffer
        ↓
K8s Units Conversion
        ↓
Change Detection
        ↓
YAML File (generated_resources.yaml)

```bash
🔁 Updated Data Flow
Kubernetes Pods
↓
Prometheus Metrics
↓
Aggregator (Feature Builder + LSTM)
↓
Predicted Metrics
↓
Safety Guard (p95 baseline)
↓
Safe Metrics
↓
YAML Generator
↓
Change Detection ✅
↓
Persistent YAML File ✅
↓
Prometheus (Recommended Metrics)
↓
Grafana Visualization
```

## 📊 System Behavior
Scenario	Outcome
First run	YAML created
Small fluctuations	No update
Significant workload change (>10%)	YAML updated
Prometheus failure	System continues safely

## 🚀 System Capability (AFTER PHASE 8)
The system now:
Observes workload behavior
Learns from real-time data
Predicts future usage
Applies safety guarantees
Generates Kubernetes configurations
Persists recommendations to disk
Avoids unnecessary updates

---

# 🎯 Final Goal

A system that:
```bash
Observe → Learn → Predict → Recommend → Adapt
```

for Kubernetes resource optimization.
