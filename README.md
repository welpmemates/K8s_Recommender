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
# Should print Hello from Docker!
docker run hello-world
```
