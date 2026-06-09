# Copyright (c) 2026 李軒杰, 黃義鈞
# Datung University — I4210 AI實務專題
#
# Build: docker buildx build --platform linux/arm64 -t ghcr.io/Saibusu/AI-course:latest .
# Run:   docker run --rm --runtime nvidia -v ~/AI-course/models:/app/models:ro <image>

FROM nvcr.io/nvidia/l4t-pytorch:r36.2.0-pth2.1-py3

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-gi \
    python3-gi-cairo \
    gir1.2-gst-plugins-base-1.0 \
    gir1.2-gstreamer-1.0 \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    libgstreamer1.0-dev \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies (no ultralytics — crashes on Jetson, use pycuda instead)
COPY requirements.txt .
RUN pip install --no-cache-dir \
    numpy \
    opencv-python-headless \
    pyyaml \
    pytest \
    pytest-cov

# Copy source
COPY src/ ./src/
COPY tests/ ./tests/
COPY live_detect.py .
COPY accuracy_baseline.json .

# Models mounted at runtime: -v ~/AI-course/models:/app/models:ro
RUN mkdir -p /app/models /app/logs

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

CMD ["python", "live_detect.py"]
