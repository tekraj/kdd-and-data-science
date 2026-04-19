#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

echo "Updating system and removing old versions of Docker..."
sudo apt-get update
sudo apt-get remove -y docker docker-engine docker.io containerd runc || true

echo "Installing prerequisites..."
sudo apt-get install -y ca-certificates curl gnupg

echo "Setting up Docker GPG key..."
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg --yes
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo "Adding Docker repository..."
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

echo "Installing Docker Engine and Docker Compose..."
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

echo "Verifying installation..."
docker --version
docker compose version

echo "Post-installation: Adding current user to the docker group..."
if ! getent group docker > /dev/null; then
    sudo groupadd docker
fi

sudo usermod -aG docker $USER

echo "------------------------------------------------------------"
echo "Installation Complete!"
echo "IMPORTANT: To run docker without sudo, please log out and log back in,"
echo "or run the command: newgrp docker"
echo "------------------------------------------------------------"

# Confirm with hello-world (uses sudo because group membership hasn't refreshed in this shell)
sudo docker run hello-world