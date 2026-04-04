# K8s Recommender

## Overview

This project builds an **online learning–based Kubernetes resource recommendation system** that learns CPU and memory requirements from real workload behavior.

Phase 1 focuses on creating a **realistic, observable workload inside Kubernetes** that generates meaningful resource usage patterns.

---

## Phase 1: Workload Simulation & Observability ✅

### Objective

Create a controlled application that:

* Generates CPU and memory load
* Produces non-deterministic request patterns
* Exposes metrics for monitoring and learning

---

## System Architecture (Phase 1)

```
Locust → FastAPI Mock App → Kubernetes Pod → Metrics Server
```

---

## Mock Application

Location:

```
mock_app/app/main.py
```

### Features

* Dynamic workload via `/work`
* Token generation per request
* CPU simulation (hashing)
* Memory simulation (optional retention)
* Prometheus metrics endpoint (`/metrics`)

Example request:

```
/work?size=10000&sleep=0.05&retain=true
```

---

## Kubernetes Deployment

Defined in:

* `deployment.yaml` 
* `service.yaml` 

### Resource Configuration

* CPU: 100m → 500m
* Memory: 128Mi → 512Mi

---

## Load Generation

Using Locust:

```
mock_app/locust/locustfile.py
```

Features:

* Randomized request sizes
* Variable latency
* Continuous load generation

---

## Metrics Exposed

From application:

* `app_requests_total`
* `app_request_duration_seconds`
* `token_cpu_estimate`
* `token_memory_estimate`
* `active_tokens`

From Kubernetes:

* CPU usage
* Memory usage

---

## How to Run

### 1. Start Kubernetes

```
minikube start
minikube addons enable metrics-server
```

---

### 2. Build Image (inside Minikube)

```
eval $(minikube docker-env)

docker build -t mock-fastapi:latest -f mock_app/docker/Dockerfile mock_app
```

---

### 3. Deploy

```
kubectl apply -f mock_app/k8s/
kubectl get pods
```

---

### 4. Test Application

```
minikube ip
```

Open:

```
http://<ip>:30007/work
http://<ip>:30007/metrics
```

---

### 5. Generate Load

```
cd mock_app/locust
locust --host=http://<ip>:30007
```

Open:

```
http://localhost:8089
```

---

### 6. Observe Metrics

```
kubectl top pods
```

---

## Key Observations (Phase 1)

* CPU usage scales with **request rate**
* Memory usage scales with **retention behavior**
* Metrics are stable and observable
* Workload is reproducible and configurable

---

## Outcome

Phase 1 successfully establishes:

* A realistic Kubernetes workload
* Reliable CPU and memory signals
* Tokenized request behavior
* Observability pipeline foundation

---

## Next Phase

Phase 2 will introduce:

* Prometheus scraping
* Grafana dashboards
* Time-series aggregation
* Feature extraction for ML

---
