import os

# ── Class definitions ─────────────────────────────────────
CLASS_NAMES = [
    "寶特瓶",   # 0  PET bottle     → GPIO Pin 11  Green
    "鐵鋁罐",   # 1  Metal can      → GPIO Pin 13  Yellow
    "紙餐盒",   # 2  Paper box      → GPIO Pin 15  Blue
    "塑膠袋",   # 3  Plastic bag    → GPIO Pin 19  White
    "鋁箔包",   # 4  Foil/Tetra Pak → GPIO Pin 21  Orange
    "一般垃圾", # 5  General waste  → GPIO Pin 23  Red
]

# ── GPIO pin mapping (Board numbering) ───────────────────
GPIO_PINS = {
    0: 11,   # 寶特瓶  → Green
    1: 13,   # 鐵鋁罐  → Yellow
    2: 15,   # 紙餐盒  → Blue (100Ω resistor)
    3: 19,   # 塑膠袋  → White (100Ω resistor)
    4: 21,   # 鋁箔包  → Orange
    5: 23,   # 一般垃圾 → Red
}
BUZZER_PIN = 17

# ── LED colors for display reference ────────────────────
LED_COLORS = {
    0: "GREEN",
    1: "YELLOW",
    2: "BLUE",
    3: "WHITE",
    4: "ORANGE",
    5: "RED",
}

# ── Model settings ───────────────────────────────────────
MODEL_ENGINE  = os.path.join(os.path.dirname(__file__), "..", "models", "waste_sorter_fp16.engine")
MODEL_PT      = os.path.join(os.path.dirname(__file__), "..", "models", "best.pt")
MODEL_PRETRAIN = "yolo26s-seg.pt"  # base model for fine-tuning (auto-downloaded by ultralytics)
INPUT_SIZE   = 416
CONF_THRESH  = 0.45

# ── Camera settings ──────────────────────────────────────
CAMERA_ID    = 0          # CSI camera via GStreamer pipeline index
CAMERA_WIDTH = 1280
CAMERA_HEIGHT= 720

# ── Behavior settings ────────────────────────────────────
LED_DURATION = 5.0        # seconds LED stays on
BUZZER_DURATION = 0.2     # seconds buzzer beeps
LOG_FILE = os.path.join(os.path.dirname(__file__), "..", "logs", "detections.csv")
