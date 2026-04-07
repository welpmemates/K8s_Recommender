# 🚀 Kubernetes Resource Recommender (Online LSTM)

A **production-style ML system** that observes Kubernetes workloads, learns resource usage patterns in real time, and generates **safe, adaptive resource recommendations**.

---

# 🧠 Core Idea

Instead of modeling raw requests directly:

```
Requests → Tokens → Resource Signatures → Time-Series Features → LSTM → Predictions → Safe Recommendations
```

We transform **unbounded workloads into structured signals** that can be learned by an online model.

---

# 🏗️ System Architecture

```
                ┌──────────────────────────┐
                │     Kubernetes Pods      │
                │   (mock FastAPI app)     │
                └────────────┬─────────────┘
                             │
                             ▼
                ┌──────────────────────────┐
                │       Prometheus         │
                │  (metrics collection)    │
                └────────────┬─────────────┘
                             │
                             ▼
                ┌──────────────────────────┐
                │        Aggregator        │
                │                          │
                │ Feature Builder          │
                │ Sliding Window           │
                │ Online LSTM              │
                │ Safety Guard (p95)       │
                │ YAML Generator           │
                │ Evaluation Engine        │
                └────────────┬─────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
 Prometheus Metrics   YAML Output        Model Evaluation
 (predictions + safe) (K8s config)       (MAE, RMSE, spikes)

                             ▼
                ┌──────────────────────────┐
                │        Grafana           │
                │  (full observability)    │
                └──────────────────────────┘
```

---

# ⚙️ Key Features

## Real-Time Learning

* Online LSTM trained continuously
* No offline dataset required

## Safety First

* p95 baseline prevents under-provisioning
* Additional 20% safety buffer

## Intelligent YAML Generation

* Converts predictions → Kubernetes resources
* Auto change detection (10% threshold)

## Full Observability

* Prediction vs actual
* Absolute error tracking
* MAE / RMSE monitoring
* Spike miss detection

---

# 📊 Evaluation Metrics

The system continuously evaluates itself:

| Metric         | Meaning                            |
| -------------- | ---------------------------------- |
| MAE            | Average prediction error           |
| RMSE           | Penalizes large failures           |
| Absolute Error | Real-time deviation                |
| Spike Miss     | Critical underprediction detection |

Example:

```
cpu_absolute_error
cpu_mae
cpu_rmse
cpu_spike_miss
```

---

# 📁 Project Structure

```
K8s_Recommender/
├── mock_app/
│   ├── app/
│   │   └── main.py
│   ├── docker/
│   │   └── Dockerfile
│   ├── k8s/
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   ├── servicemonitor.yaml
│   ├── locust/
│   │   └── locust.py
│
├── infra/
│   ├── aggregator/
│   │   ├── main.py              # Core pipeline
│   │   ├── config.py
│   │   ├── feature_builder.py
│   │   ├── prom_client.py
│   │   ├── yaml_generator.py
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   ├── servicemonitor.yaml
│   │   ├── Dockerfile
│   │
│   ├── ml/
│   │   ├── model.py             # LSTM
│   │   ├── trainer.py
│   │   ├── dataset.py
│   │   ├── utils.py
│   │   ├── config.py
│   │
│   ├── grafana/
│   │   └── dashboard.json
│
├── README.md
└── requirements.txt
```

---

# 🔁 End-to-End Pipeline

```
K8s → Prometheus → Aggregator → LSTM → Prediction
→ Safety Guard → YAML → Change Detection
→ Evaluation → Prometheus → Grafana
```

---

# 🚀 How to Run

## 1. Start Minikube

```bash
minikube start --driver=docker
minikube addons enable metrics-server
```

## 2. Build Mock App

```bash
eval $(minikube docker-env)
docker build -t mock-fastapi:latest -f mock_app/docker/Dockerfile mock_app
```

## 3. Deploy App

```bash
kubectl apply -f mock_app/k8s/
```

## 4. Install Monitoring

```bash
helm install prometheus prometheus-community/kube-prometheus-stack -n monitoring
```

## 5. Deploy Aggregator

```bash
kubectl apply -f infra/aggregator/
```

## 6. Generate Load

```bash
cd mock_app/locust
locust --host=http://<minikube-ip>:30007
```

---

# 📊 Grafana Dashboard

The dashboard provides:

### Core System

* Actual vs Predicted vs Safe
* Safety margins

### Model Evaluation

* MAE / RMSE
* Absolute error

### Failure Detection

* Spike miss alerts
* Spike miss rate

### Output

* Recommended CPU / Memory

---

# 🎯 What This Project Demonstrates

* Real-time ML systems design
* Online learning (streaming LSTM)
* Kubernetes observability
* Production-safe ML deployment
* Reliability engineering for ML systems

---

# 🧠 Final Insight

This system is not just:

```
ML model → prediction
```

It is:

```
Observe → Learn → Predict → Safeguard → Evaluate → Act
```
