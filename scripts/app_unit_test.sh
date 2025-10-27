docker run --rm -e DISPLAY=${DISPLAY} ghcr.io/j-automationlab/agent:latest pytest -v ./tests
docker run --rm -e DISPLAY=${DISPLAY} ghcr.io/j-automationlab/simulator:latest pytest -v ./tests