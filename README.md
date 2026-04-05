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

# 🎯 Phase 2 Outcome

* Real-time workload simulation
* Prometheus metrics pipeline
* Grafana visualization
* CPU & memory observability
* Request-level behavioral tracking

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

## 🎯 Phase 3 Outcome

- Real-time feature aggregation pipeline built  
- Prometheus metrics converted into ML-ready inputs  
- Sliding window sequences generated for temporal modeling  
- System fully prepared for LSTM integration  

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

## 🎯 Phase 4 Outcome

- Online LSTM training implemented
- Stable learning achieved
- Real-time predictions generated
- Fully integrated into pipeline

## ⚠️ Notes

- Initial predictions may be inaccurate
- Model improves over time
- Continuous load is required

---

# 🎯 Final Goal

A system that:
```bash
Observe → Learn → Predict → Recommend → Adapt
```

for Kubernetes resource optimization.
