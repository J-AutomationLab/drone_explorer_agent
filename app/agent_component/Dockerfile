FROM pytorch/pytorch:2.7.1-cuda11.8-cudnn9-runtime

# Set working directory
WORKDIR /home/hostuser/workspace/src

# Install system dependencies for OpenCV, PIL, etc.
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-dev \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir \
    numpy \
    opencv-python \
    paho-mqtt \
    pillow \
    torch \
    transformers \
    sentence-transformers \
    networkx \
    langgraph \ 
    langchain \
    smolagents 

# Optional: bash as default entrypoint
ENTRYPOINT ["/bin/bash"]
