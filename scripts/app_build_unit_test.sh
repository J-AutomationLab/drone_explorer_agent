#!/usr/bin/env bash
set -e  # exit on error

# --- Build all images ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(realpath "$SCRIPT_DIR/..")"

docker compose -f "$REPO_ROOT/app/docker-compose.yml" build

# --- Run all unit tests --- 
docker compose -f "$REPO_ROOT/app/docker-compose.yml" run  --rm -e DISPLAY=${DISPLAY} --entrypoint pytest agent -v ./tests -p no:warnings
docker compose -f "$REPO_ROOT/app/docker-compose.yml" run  --rm -e DISPLAY=${DISPLAY} --entrypoint pytest simulator-headless -v ./tests -p no:warnings
