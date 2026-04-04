# K8s Recommender

Online Learning-Based Kubernetes Resource Recommendation System using tokenized request behavior and LSTM.

This project builds a system that observes application resource behavior inside Kubernetes and learns to recommend optimal CPU and memory configurations using telemetry-driven machine learning.

---

# 🔧 Environment Setup

## Install Base Dependencies

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

# ☸️ Install Kubernetes Tools

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

# ⚙️ Install Helm

```bash
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
helm version
```

---

# 🐍 Python Environment Setup

## Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

## Install Required Libraries

```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install numpy pandas scikit-learn
pip install prometheus-client requests pyyaml matplotlib
pip install fastapi uvicorn locust
```

## Verify Python Environment

```bash
python - <<EOF
import torch, numpy, pandas, sklearn
import prometheus_client, yaml, matplotlib

print("All imports OK")
print("Torch version:", torch.__version__)
print("CUDA available:", torch.cuda.is_available())
EOF
```

---

# 🚀 Running the Mock Application (Phase 1)

## Start Kubernetes

```bash
minikube start
minikube addons enable metrics-server
```

## Verify Metrics Server

```bash
kubectl get pods -n kube-system | grep metrics
```

---

## Build Docker Image (inside Minikube)

```bash
eval $(minikube docker-env)

docker build -t mock-fastapi:latest -f mock_app/docker/Dockerfile mock_app
docker images | grep mock-fastapi
```

---

## Deploy Application

```bash
kubectl apply -f mock_app/k8s/
kubectl get pods
kubectl logs deployment/mock-app
```

---

# 🧪 Phase 1 Testing

## Get Cluster IP

```bash
minikube ip
```

---

## Test Application

```bash
curl "http://<ip>:30007/work?size=10000"
```

---

## Test Metrics Endpoint

Open in browser:

```
http://<ip>:30007/metrics
```

---

## View Kubernetes Resource Usage

```bash
kubectl top pods
```

---

## Generate Load (Locust)

```bash
cd mock_app/locust
locust --host=http://<ip>:30007
```

Open:

```
http://localhost:8089
```

---

# 📊 Phase 1 Outcome

Phase 1 establishes:

* A realistic Kubernetes workload
* Dynamic CPU and memory behavior
* Tokenized request generation
* Prometheus-compatible metrics exposure
* Reliable resource observability

---

# ⏭️ Next Phase

Phase 2 introduces:

* Prometheus scraping
* Grafana dashboards
* Time-series aggregation
* Feature engineering for LSTM

---
