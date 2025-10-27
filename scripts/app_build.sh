#!/usr/bin/env bash
set -e  # exit on error

# --- Build all images ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(realpath "$SCRIPT_DIR/..")"

docker compose -f "$REPO_ROOT/app/docker-compose.yml" build

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