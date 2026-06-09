# 智慧零接觸垃圾分類與數據收集系統
**Smart Touchless Waste Sorting & Data Collection System**

114-2 AI實務課程 I4210 ｜ 李軒杰 黃義鈞 ｜ 大同大學

[![CI](https://github.com/Saibusu/AI-course/actions/workflows/ci.yml/badge.svg)](https://github.com/Saibusu/AI-course/actions/workflows/ci.yml)

---

## 系統概述

以 Jetson Orin Nano 8GB 為核心的 Edge AI 垃圾分類系統，辨識 **5 類**垃圾並透過 GPIO LED 指示燈引導投放，全程無需觸碰。

**技術棧**：YOLO26m（detect）+ TensorRT FP16 + pycuda + Jetson GPIO + IMX219 CSI 攝影機

> **推論路徑**：`live_detect.py` 使用純 pycuda 操作 TRT engine，完全繞過 PyTorch。
> Jetson JetPack PyTorch 2.5.0a0+nv24.08 在 aarch64 上有 C++ crash，詳見 [推論修復紀錄](docs/progress/2026-06-08-jetson-inference-fix.md)。

---

## 辨識類別（5-class，v5）

| ID | 中文 | 英文 | LED 顏色 | GPIO Pin | 電阻 |
|----|------|------|---------|---------|------|
| 0 | 寶特瓶 | PET Bottle | 🟢 綠 | Pin 11 | 220Ω |
| 1 | 鐵鋁罐 | Metal Can | 🟡 黃 | Pin 13 | 220Ω |
| 2 | 紙餐盒 | Paper Box | 🔵 藍 | Pin 15 | 100Ω |
| 3 | 塑膠袋 | Plastic Bag | ⚪ 白 | Pin 21 | 100Ω |
| 4 | 一般垃圾 | General Waste | 🔴 紅 | Pin 23 | 220Ω |

> 鋁箔包（原 Class 4）已移除：Roboflow 資料集樣本不足，歸入一般垃圾。

---

## 快速開始

### 在 Jetson 上執行

```bash
git clone https://github.com/Saibusu/AI-course.git
cd AI-course
python live_detect.py
```

### 建立 TensorRT Engine（一次性，約 5-10 分鐘）

```bash
# 在 Jetson 執行
/usr/src/tensorrt/bin/trtexec \
  --onnx=models/best_v5.onnx \
  --saveEngine=models/best_v5.engine \
  --fp16
```

ONNX 匯出（Windows/Mac）：
```bash
python -c "from ultralytics import YOLO; YOLO('best_v5.pt').export(format='onnx', imgsz=416, simplify=True, opset=12)"
scp best_v5.onnx jetson@<IP>:~/AI-course/models/
```

### 執行測試

```bash
pip install pdm && pdm install
pdm run pytest tests/ -v --cov=src --cov-fail-under=90
```

---

## 訓練模型

訓練使用 Kaggle（30h/週免費 GPU）：

1. 開啟 `train_kaggle.ipynb`
2. Settings → Accelerator → GPU T4 x2
3. Add-ons → Secrets → 新增 `ROBOFLOW_API_KEY`（名稱必須完全一致）
4. 依序執行 Cell 1–7

資料集：YOLO Waste Detection (ProjectVerba, Roboflow) — 5,460 張，42 類 → 5 類 mapping

---

## 檔案架構

```
AI-course/
├── .github/workflows/
│   ├── ci.yml             # 5-stage CI/CD pipeline
│   └── deploy.yml         # 部署至 Jetson
├── src/
│   ├── config.py          # 5-class 設定、GPIO pins、CONF_THRESH=0.55
│   ├── detector.py        # YOLO26m 推論封裝
│   ├── gpio_controller.py # GPIO LED 控制（含 mock mode）
│   ├── camera.py          # CSI 攝影機（GStreamer）
│   ├── logger_util.py     # 辨識記錄 CSV
│   └── main.py            # 主程式進入點
├── live_detect.py         # TRT+pycuda 推論（Jetson 實際使用）
├── train_kaggle.ipynb     # Kaggle 訓練 Notebook（v6）
├── train_colab.ipynb      # Colab 訓練 Notebook（v5，備用）
├── tests/
│   ├── test_detector.py   # WasteDetector 單元測試
│   └── test_gpio.py       # GPIOController 單元測試
├── docs/adr/              # ADR-001/002/003（均 Accepted）
├── docs/specs/            # SPEC-001/002/003
├── docs/progress/         # 操作日誌
├── deploy/                # Docker Compose、部署腳本
├── scripts/
│   └── parse_tegrastats.py
├── hardware/wiring.md
├── Dockerfile
├── pyproject.toml
├── accuracy_baseline.json
└── models/                # 模型權重（.gitignore 排除）
```

---

## 硬體需求

| 元件 | 規格 |
|------|------|
| 主控板 | Jetson Orin Nano 8GB |
| 攝影機 | IMX219 CSI-2 |
| LED | 高亮 5mm × 5（綠/黃/藍/白/紅）|
| 電阻 | 220Ω × 3、100Ω × 2 |

詳細接線見 [hardware/wiring.md](hardware/wiring.md)。

---

## 模型性能（v5，已部署）

| 指標 | 數值 |
|------|------|
| mAP@50 | 0.755 |
| 推論速度（Jetson）| ~15 FPS |
| 單幀延遲 | ~20ms |
| 信心門檻 | 0.55 |
| 量化 | TensorRT FP16 |

---

## ASP 文件

| 文件 | 狀態 | 說明 |
|------|------|------|
| [ADR-001](docs/adr/ADR-001-Use-YOLOE-with-TensorRT-FP16-for-Waste-Classification.md) | Accepted | 模型：YOLO26m + TRT FP16 |
| [ADR-002](docs/adr/ADR-002-Dataset-Strategy-TACO-plus-Custom-6class.md) | Accepted | 資料集：Roboflow 5-class mapping |
| [ADR-003](docs/adr/ADR-003-GPIO-LED-Actuation-Design.md) | Accepted | GPIO LED 5-class 設計 |

---

## 安全性說明

- Roboflow API Key **不** 存入 git，僅存於 Kaggle Secrets / Colab runtime
- `models/*.pt`、`models/*.engine`、`logs/` 均在 `.gitignore` 中

---

*Last updated: 2026-06-09 | v5 deployed (mAP=0.755) | v6 training on Kaggle*
