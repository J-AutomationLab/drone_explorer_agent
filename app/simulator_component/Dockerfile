FROM cyberbotics/webots:latest

# Avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies for OpenCV, Qt (xcb), etc.
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-dev \
    tree \
    libsm6 \
    libxext6 \
    libxrender1 \
    libxrender-dev \
    libxkbcommon-x11-0 \
    libxcb1 \
    libxcb-xinerama0 \
    libxcb-cursor0 \
    libglu1-mesa \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir \
    numpy \
    opencv-python \
    paho-mqtt \
    pillow \
    pytest

# Environment variables for headless / offscreen mode
ENV QT_X11_NO_MITSHM=1
ENV WEBOTS_HEADLESS=1
ENV WEBOTS_SUPPRESS_ROOT_WARNING=1

# Set working directory
WORKDIR /home/hostuser/workspace/simulator_component
ENV PYTHONPATH=/home/hostuser/workspace/simulator_component

# Run Webots headless in headless or gui mode
ENTRYPOINT ["/bin/bash", "-c", "\
if [ \"$WEBOTS_MODE\" = \"gui\" ]; then \
    webots --batch --stdout --stderr --mode=realtime ./worlds/my_complete_apartment.wbt > /home/hostuser/workspace/simulator_component/tests/logs/gui.log 2>&1 || exit 1; \
else \
    Xvfb :99 -screen 0 1920x1080x24 & \
    export DISPLAY=:99 && \
    webots --batch --minimize --stdout --stderr --mode=realtime ./worlds/my_complete_apartment.wbt > /home/hostuser/workspace/simulator_component/tests/logs/headless.log 2>&1 || exit 1; \
fi"]

COPY controllers ./controllers
COPY protos ./protos
COPY worlds ./worlds
COPY tests ./tests
COPY src ./src
COPY config/preferences.xml /home/hostuser/workspace/.config/Webots/preferences.xml

# WEBOTS_MODE=gui docker compose up / WEBOTS_MODE=headless docker compose up [default]


CMD ["/bin/bash"] 