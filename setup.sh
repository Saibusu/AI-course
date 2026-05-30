#!/bin/bash
# Jetson Orin Nano — 環境初始化腳本
# Usage: bash setup.sh
# 在 Jetson 上執行一次即可

set -e

echo "=== Smart Waste Sorter — Jetson Setup ==="
echo "JetPack version check:"
cat /etc/nv_tegra_release 2>/dev/null || echo "(nv_tegra_release not found)"

# ── 1. System packages ───────────────────────────────────
echo ""
echo "[1/6] Installing system packages..."
sudo apt-get update -q
sudo apt-get install -y -q \
    python3-pip \
    python3-dev \
    libgstreamer1.0-dev \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    libopencv-dev \
    python3-opencv

# ── 2. GPIO permissions ──────────────────────────────────
echo ""
echo "[2/6] Setting GPIO permissions..."
sudo groupadd -f gpio
sudo usermod -aG gpio "$USER"
sudo chmod a+rw /dev/gpiochip* 2>/dev/null || true

# ── 3. Python packages ───────────────────────────────────
echo ""
echo "[3/6] Installing Python packages..."
pip3 install --upgrade pip
pip3 install \
    ultralytics \
    Jetson.GPIO \
    numpy \
    opencv-python-headless \
    pytest

# ── 4. Project directory ─────────────────────────────────
echo ""
echo "[4/6] Creating project directories..."
mkdir -p ~/final/models
mkdir -p ~/final/logs
mkdir -p ~/final/data/dataset

# ── 5. Verify CUDA ───────────────────────────────────────
echo ""
echo "[5/6] CUDA check:"
python3 -c "import torch; print(f'PyTorch: {torch.__version__}'); print(f'CUDA available: {torch.cuda.is_available()}')" || \
  echo "PyTorch not installed (install via: pip3 install torch torchvision --index-url <jetson-wheel-url>)"

# ── 6. Camera test ───────────────────────────────────────
echo ""
echo "[6/6] Camera check:"
python3 -c "
import cv2
cap = cv2.VideoCapture(0)
if cap.isOpened():
    print('Camera /dev/video0: OK')
    cap.release()
else:
    print('WARNING: Camera not detected. Check CSI connection.')
"

echo ""
echo "=== Setup complete ==="
echo "Next steps:"
echo "  1. Copy trained model:  scp best.pt jetson@172.20.10.2:~/final/models/"
echo "  2. Export TensorRT:     cd ~/final && python3 src/main.py --export-trt"
echo "  3. Run system:          cd ~/final && python3 src/main.py"
echo ""
echo "NOTE: Re-login or run 'newgrp gpio' for GPIO permissions to take effect."
