FROM nvcr.io/nvidia/l4t-jetpack:r36.4.0

# Avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# System deps you might want for building/running MediaPipe
RUN apt-get update && apt-get install -y \
    git \
    curl \
    python3-pip \
    python3-dev \
    build-essential \
    cmake \
    unzip \
    pkg-config \
    libopencv-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# Upgrade pip inside container
RUN pip3 install --upgrade pip && \
    pip3 install --no-cache-dir \
        flask \
        numpy \
        mediapipe
