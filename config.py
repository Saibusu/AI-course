"""
config.py — 系統全域設定
智慧零接觸垃圾分類系統 | Jetson Orin Nano

環境變數優先：可透過 docker-compose / 指令列覆寫設定
  WASTE_MODEL_PATH=models/best.pt python main.py
"""

import os

# ──────────────────────────────────────────────
# 執行環境偵測
#   ENV=dev     → PC 開發模式（Mock GPIO、USB 攝影機）
#   ENV=jetson  → Jetson 正式部署
# ──────────────────────────────────────────────
ENV = os.getenv("ENV", "dev")          # "dev" | "jetson"
IS_JETSON = (ENV == "jetson")

# ──────────────────────────────────────────────
# 模型設定
# ──────────────────────────────────────────────
# PC 開發階段先用官方 yolov8n.pt；Jetson 部署換成 .engine
_default_model = (
    "models/waste_classifier.engine" if IS_JETSON
    else "models/waste_classifier.pt"
)
MODEL_PATH          = os.getenv("WASTE_MODEL_PATH", _default_model)
MODEL_ONNX_PATH     = "models/waste_classifier.onnx"
INPUT_SIZE          = (416, 416)
CONFIDENCE_THRESHOLD = float(os.getenv("CONF_THRESH", "0.60"))
NMS_IOU_THRESHOLD   = 0.45

# ──────────────────────────────────────────────
# 垃圾分類定義（class_id → 中文、英文、LED顏色）
# ──────────────────────────────────────────────
WASTE_CLASSES = {
    0: {"zh": "寶特瓶",   "en": "PET Bottle",      "led": "green"},
    1: {"zh": "鐵鋁罐",   "en": "Aluminum Can",     "led": "yellow"},
    2: {"zh": "紙餐盒",   "en": "Paper Container",  "led": "blue"},
    3: {"zh": "塑膠袋",   "en": "Plastic Bag",      "led": "white"},
    4: {"zh": "鋁箔包",   "en": "Foil Package",     "led": "orange"},
    5: {"zh": "一般垃圾", "en": "General Waste",    "led": "red"},
}
DEFAULT_CLASS_ID = 5   # fallback → 一般垃圾

# ──────────────────────────────────────────────
# GPIO 腳位（Jetson BCM 編號）
# ──────────────────────────────────────────────
GPIO_LED = {
    "green":  12,
    "yellow": 16,
    "blue":   20,
    "white":  19,
    "orange": 23,
    "red":    21,
}
GPIO_BUZZER = 26

# ──────────────────────────────────────────────
# 致動器行為
# ──────────────────────────────────────────────
LED_ON_DURATION   = float(os.getenv("LED_DURATION", "5.0"))
BUZZER_DURATION   = 0.15
COOLDOWN_DURATION = 1.0

# ──────────────────────────────────────────────
# 攝影機設定
# ──────────────────────────────────────────────
CAMERA_ID     = int(os.getenv("CAMERA_ID", "0"))
CAMERA_WIDTH  = 1280
CAMERA_HEIGHT = 720
CAMERA_FPS    = 30
CAMERA_FLIP   = int(os.getenv("CAMERA_FLIP", "0"))  # 0=不翻轉 2=上下翻轉

# ──────────────────────────────────────────────
# 系統行為
# ──────────────────────────────────────────────
SHOW_PREVIEW    = os.getenv("SHOW_PREVIEW", "true").lower() == "true"
LOG_PREDICTIONS = True
LOG_PATH        = "logs/predictions.csv"
