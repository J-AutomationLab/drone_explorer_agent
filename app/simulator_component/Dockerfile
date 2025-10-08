FROM cyberbotics/webots:latest

# Install system dependencies for OpenCV, PIL, etc.
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-dev \
    tree \
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
    pytest

# Set working directory
WORKDIR /home/hostuser/workspace/simulator_component

CMD ["/bin/bash"]
