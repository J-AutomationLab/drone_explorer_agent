FROM nvidia/cuda:12.1.1-cudnn8-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies 
RUN apt-get update && apt-get install -y \ 
    python3.10 \
    python3-pip \
    bash \
    tree \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Ensure python and pip point to the same binary
RUN ln -sf /usr/bin/python3 /usr/bin/python && ln -sf /usr/bin/pip3 /usr/bin/pip

# Install PyTorch (with CUDA) and all other Python deps
RUN pip install --no-cache-dir --prefer-binary \
    numpy \
    pytest \
    paho-mqtt \
    pillow \
    opencv-python-headless \
    networkx \
    transformers \
    sentence-transformers \
    langgraph 


# Set working directory
WORKDIR /home/hostuser/workspace/agent_component

# Save app 
COPY src ./src 
COPY tests ./tests 

# Optional: bash as default entrypoint
CMD ["/bin/bash"]

# run tests with: docker compose run --rm --entrypoint pytest agent -v tests 
