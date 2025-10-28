#!/usr/bin/env bash
set -e  # exit on error

# --- GHCR Login ---
if [[ -z "$GH_TOKEN" ]]; then
  echo "⚠️  GH_TOKEN not set. Please enter your GitHub Personal Access Token or Export it before calling this script:"
  read -s GH_TOKEN
fi

echo "$GH_TOKEN" | docker login ghcr.io 

# --- Push all images ---
docker push ghcr.io/j-automationlab/mqtt_broker:latest 
docker push ghcr.io/j-automationlab/simulator:latest 
docker push ghcr.io/j-automationlab/agent:latest 