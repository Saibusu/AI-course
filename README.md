# 智慧零接觸垃圾分類與數據收集系統
**Smart Touchless Waste Sorting & Data Collection System**

114-2 AI實務課程 ｜ 李軒杰 黃義鈞

---

## 系統概述

以 Jetson Orin Nano 為核心的 Edge AI 垃圾分類系統，辨識 6 類垃圾並透過 GPIO LED 指示燈引導投放，全程無需觸碰。

**技術棧**：YOLO26s-seg + TensorRT FP16 + Jetson GPIO + IMX219 CSI 攝影機

## 辨識類別

| ID | 類別 | LED 顏色 | GPIO Pin |
|----|------|---------|----------|
| 0 | 寶特瓶 | 綠 | 11 |
| 1 | 鐵鋁罐 | 黃 | 13 |
| 2 | 紙餐盒 | 藍 | 15 |
| 3 | 塑膠袋 | 白 | 19 |
| 4 | 鋁箔包 | 橙 | 21 |
| 5 | 一般垃圾 | 紅 | 23 |

## 快速開始

### 在 Jetson 上執行

```bash
# 1. 環境初始化（一次性）
bash setup.sh

# 2. 複製訓練好的模型
cp best.pt models/

# 3. 轉換 TensorRT（一次性，約 10–15 分鐘）
python src/main.py --export-trt

# 4. 啟動系統
python src/main.py
```

### 訓練模型（PC / Colab）

```bash
# 準備資料集
python data/prepare_taco.py       # TACO → YOLO 格式
python data/prepare_trashnet.py   # TrashNet → YOLO 格式
python data/merge_datasets.py     # 三層資料合併

# 訓練 YOLO26s-seg
python data/train.py --data data/merged/data.yaml --epochs 50
```

### 從 PC 傳送到 Jetson

```bash
scp -r src/ requirements.txt setup.sh models/best.pt \
    jetson@172.20.10.2:~/final/
```

### 執行測試

```bash
pip install pytest
python -m pytest tests/ -v
```

## 檔案架構

```
├── src/
│   ├── main.py            # 主程式入口
│   ├── detector.py        # YOLO26 推論封裝
│   ├── gpio_controller.py # GPIO LED 控制
│   ├── camera.py          # CSI 攝影機
│   ├── logger_util.py     # 辨識記錄 CSV
│   └── config.py          # 參數設定
├── data/
│   ├── prepare_taco.py    # TACO 轉換腳本
│   ├── prepare_trashnet.py# TrashNet 轉換腳本
│   ├── merge_datasets.py  # 資料集合併
│   └── train.py           # 訓練腳本
├── tests/                 # 單元測試
├── hardware/wiring.md     # 詳細接線圖
├── docs/adr/              # 架構決策記錄（3 份，全部 Accepted）
├── docs/specs/            # 功能規格（3 份）
├── models/                # 模型權重（不納入 git）
├── logs/                  # 辨識記錄 CSV（不納入 git）
└── setup.sh               # Jetson 環境初始化
```

## 硬體需求

| 元件 | 規格 |
|------|------|
| 主控板 | Jetson Orin Nano 8GB |
| 攝影機 | IMX219 CSI-2 |
| LED | 高亮 5mm × 6（綠/黃/藍/白/橙/紅）|
| 電阻 | 220Ω × 4、100Ω × 2 |
| 蜂鳴器 | 有源，3.3V |

詳細接線見 [hardware/wiring.md](hardware/wiring.md)。

## ASP 文件

| 文件 | 說明 |
|------|------|
| [ADR-001](docs/adr/ADR-001-Use-YOLOE-with-TensorRT-FP16-for-Waste-Classification.md) | 模型選擇：YOLO26s-seg + TensorRT FP16 |
| [ADR-002](docs/adr/ADR-002-Dataset-Strategy-TACO-plus-Custom-6class.md) | 資料集：TACO + TrashNet + 自拍三層策略 |
| [ADR-003](docs/adr/ADR-003-GPIO-LED-Actuation-Design.md) | GPIO LED 致動設計 |
