#!/usr/bin/env python3
# Copyright (c) 2026 李軒杰, 黃義鈞
# Datung University — I4210 AI實務專題

import os

# ── Class definitions (5-class, v5) ──────────────────────
CLASS_NAMES = [
    "寶特瓶",   # 0  PET bottle   → GPIO Pin 11  Green
    "鐵鋁罐",   # 1  Metal can    → GPIO Pin 13  Yellow
    "紙餐盒",   # 2  Paper box    → GPIO Pin 15  Blue
    "塑膠袋",   # 3  Plastic bag  → GPIO Pin 21  White
    "一般垃圾", # 4  General      → GPIO Pin 23  Red
]

# ── GPIO pin mapping (Board numbering) ───────────────────
GPIO_PINS = {
    0: 11,   # 寶特瓶  → Green
    1: 13,   # 鐵鋁罐  → Yellow
    2: 15,   # 紙餐盒  → Blue  (100Ω)
    3: 21,   # 塑膠袋  → White (100Ω)  ← 移至 Pin 21（原鋁箔包位置）
    4: 23,   # 一般垃圾 → Red
    # Pin 19 停用（原塑膠袋位置）
}
BUZZER_PIN = None

# ── LED colors for display reference ────────────────────
LED_COLORS = {
    0: "GREEN",
    1: "YELLOW",
    2: "BLUE",
    3: "WHITE",
    4: "RED",
}

# ── Model settings ───────────────────────────────────────
MODEL_ENGINE  = os.path.join(os.path.dirname(__file__), "..", "models", "best_v5.engine")
MODEL_PT      = os.path.join(os.path.dirname(__file__), "..", "models", "best_v5.pt")
MODEL_PRETRAIN = "yolo26m.pt"
INPUT_SIZE   = 416
CONF_THRESH  = 0.55

# ── Camera settings ──────────────────────────────────────
CAMERA_ID    = 0          # CSI camera via GStreamer pipeline index
CAMERA_WIDTH = 1280
CAMERA_HEIGHT= 720

# ── Behavior settings ────────────────────────────────────
LED_DURATION = 5.0        # seconds LED stays on
BUZZER_DURATION = 0.2     # seconds buzzer beeps
LOG_FILE = os.path.join(os.path.dirname(__file__), "..", "logs", "detections.csv")
