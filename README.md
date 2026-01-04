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
