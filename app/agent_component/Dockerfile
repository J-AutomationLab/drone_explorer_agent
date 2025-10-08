FROM pytorch/pytorch:2.7.1-cuda11.8-cudnn9-devel 

# Install system dependencies for OpenCV, PIL, etc.
RUN apt-get update && apt-get install -y \
    tree \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Conda-only packages: pytest mainly
RUN conda install -y pytest && conda clean -ya

# Install pip-only packages
RUN pip install --no-cache-dir paho-mqtt pillow opencv-python networkx transformers sentence-transformers langgraph langchain smolagents

# Set working directory
WORKDIR /home/hostuser/workspace/agent_component

# Optional: ensure conda environment is activated for non-interactive shells
SHELL ["conda", "run", "-n", "base", "/bin/bash", "-c"]

# Optional: bash as default entrypoint
CMD ["/bin/bash"]
