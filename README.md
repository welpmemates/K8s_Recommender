# K8s_Recommender
Online Learning-Based Kubernetes Resource Recommendation System Using Tokenized Request Behavior and LSTM.<br>
<br>
This project builds a system that observes application resource behavior inside Kubernetes and learns to recommend optimal CPU and memory configurations using telemetry-driven machine learning.<br>

### Environment Setup
Install Base Dependencies<br>
```
sudo apt update
sudo apt upgrade -y

sudo apt install -y curl
sudo apt install -y wget
sudo apt install -y git
sudo apt install -y build-essential
sudo apt install -y ca-certificates
sudo apt install -y software-properties-common
sudo apt install -y docker.io
```

Verify Installations<br>
```
apt --version
curl --version
git --version
gcc --version
```

Docker Setup<br>
```
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker $USER
newgrp docker
```

Verify docker<br>
```
docker --version
docker run hello-world
```

Install Kubectl<br>
```
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"

sudo install kubectl /usr/local/bin/kubectl
kubectl version --client
```

Install Minikube
```
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64

sudo install minikube-linux-amd64 /usr/local/bin/minikube
minikube version
```

Start minikube<br>
```
minikube start --driver=docker
kubectl get nodes
```

Install Helm<br>
```
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
helm version
```

Python Environment Setup<br>
```
# Create Virtual environment
python3 -m venv venv
source venv/bin/activate

# Install libraries:
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install numpy
pip install pandas
pip install scikit-learn
pip install prometheus-client
pip install requests
pip install pyyaml
pip install matplotlib

# Verify python environment
python - <<EOF
import torch
import numpy
import pandas
import sklearn
import prometheus_client
import yaml
import matplotlib

print("All imports OK")
print("Torch version:", torch.__version__)
print("CUDA available:", torch.cuda.is_available())
EOF
```

### Running the mock application
Start Kubernetes<br>
```
minikube start
minikube addons enable metrics-server
```

Verify metrics API<br>
```
# You should see (metrics-server-xxxxx Running)
kubectl get pods -n kube-system | grep metrics
```

Build Docker Image inside minikube<br>
```
eval $(minikube docker-env)

docker build -t mock-fastapi:latest -f mock_app/docker/Dockerfile mock_app

# Verify
docker images | grep mock-fastapi
```

Deploy Application to Kubernetes<br>
```
kubectl apply -f mock_app/k8s/

# Check pod status (you should see: mock-app-xxxxx 1/1 Running)
kubectl get pods

# Verify application logs (you should see: Uvicorn running on http://0.0.0.0:8000)
kubectl logs deployment/mock-app
```

### P1 Testing
Get Cluster IP<br>
```
# Example: 192.168.49.2
minikube ip
```

Test application endpoint<br>
```
curl "http://192.168.49.2:30007/work?size=10000"
```

Test Prometheus Metrics Endpoint<br>
```
# In browser open
http://192.168.49.2:30007/metrics
```

Kubernetes Resource Metrics<br>
```
kubectl top pods
```

Generate Load with locust<br>
```
cd mock_app/locust
locust --host=http://192.168.49.2:30007

# Open in browser
http://localhost:8089

# Observe Load
kubectl top pods
```