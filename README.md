# K8s_Recommender (Ubuntu)
Run the following commands to setup the environment
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

Run the following commands to check if everything installed properly
```
apt --version
curl --version
git --version
gcc --version
```

Verify that docker is installed correctly or not
```
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker $USER
newgrp docker
docker --version
docker run hello-world
```
Install kubectl (Kubernetes CLI)
```
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install kubectl /usr/local/bin/kubectl
kubectl version --client
```

Install Minikube (Local K8s Cluster)
```
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube
minikube version
```

Start Minikube (Docker Driver)
```
minikube start --driver=docker
kubectl get nodes
```

Install Helm (Needed for Prometheus/Grafana)
```
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
helm version
```

Python Stepup
```
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install numpy
pip install pandas
pip install scikit-learn
pip install prometheus-client
pip install requests
pip install pyyaml
pip install matplotlib
```

Verifying imports
```
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

Sanity check
```
docker --version
kubectl version --client
minikube status
helm version
docker ps
kubectl get nodes
```

To Start (Everytime)
```
cd K8s_Recommender
source venv/bin/activate
```

To start the mock app to train
```(from the main git folder)
minikube start
minikube addons enable metrics-server

# wait 30s and verify if Mertics API is alive or not
kubectl get pods -n kube-system | grep metrics
# you must see: metrics-server-xxxxx   Running

# build docker image
eval $(minikube docker-env)

# build app with context
docker build -t mock-fastapi:latest -f mock_app/docker/Dockerfile mock_app

# sanity check (you should see it listed)
docker images | grep mock-fastapi

# Apply manifests to k8s
kubectl apply -f mock_app/k8s/

# check pod (should see: mock-app-xxxxx   1/1   Running)
kubectl get pods

# sanity check (see: Uvicorn running on http://0.0.0.0:8000)
kubectl logs deployment/mock-app

# get minikube ip
minikube ip

# K8s metrics sanity check
kubectl top pods

# Start locust
cd mock_app/locust
locust --host=http://192.168.49.2:30007

# Open another terminal and check
kubectl top pods
```