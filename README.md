# 智慧零接觸垃圾分類系統
**Smart Touchless Waste Sorting & Data Collection System**  
Jetson Orin Nano × YOLO26 × TensorRT FP16

---

## 目錄結構

```
waste_sorting_system/
├── main.py                    # 主程式（SENSE→PROCESS→DECIDE→ACT 閉環）
├── classifier.py              # YOLO 推論器（TensorRT / PyTorch 自動切換）
├── camera.py                  # 攝影機封裝（CSI-2 / USB 自動切換）
├── gpio_controller.py         # LED & 蜂鳴器 GPIO（真實 / Mock 自動切換）
├── prediction_logger.py       # 辨識結果 CSV 紀錄器（執行緒安全）
├── config.py                  # 全域設定（支援環境變數覆寫）
├── train.py                   # YOLO26 訓練腳本
├── export_tensorrt.py         # .pt → TensorRT FP16 engine 轉換工具
├── test_gpio.py               # GPIO 硬體接線測試（Jetson 用）
├── requirements.dev.txt       # PC 開發依賴
├── requirements.jetson.txt    # Jetson 部署依賴
├── scripts/
│   ├── download_dataset.py    # 下載 Roboflow 資料集並重映射 6 類
│   └── prepare_openimages.py  # 下載 Open Images V7 資料集
├── tests/
│   ├── test_classifier.py     # 分類器單元測試
│   └── test_gpio.py           # GPIO 控制器單元測試
├── dataset/
│   ├── data.yaml              # 資料集描述（6 類）
│   ├── train/                 # 訓練集
│   └── valid/                 # 驗證集
├── docker/
│   ├── Dockerfile.dev         # PC 開發映像
│   └── Dockerfile.jetson      # Jetson 正式部署映像
├── docker-compose.yml         # PC 開發 compose
├── docker-compose.jetson.yml  # Jetson 部署 compose
├── Makefile                   # 快速指令（make help 查看）
├── models/                    # 模型目錄（.pt / .engine）
└── logs/                      # 辨識記錄 CSV
```

---

## 環境自動切換邏輯

| 環境變數 `ENV=` | GPIO | 攝影機 | 推論後端 |
|---|---|---|---|
| `dev`（預設）| MockGPIO（Console 輸出） | USB `/dev/video0` | PyTorch CPU |
| `jetson` | Jetson.GPIO（真實硬體） | IMX219 CSI-2 GStreamer | TensorRT FP16 |

---

## 垃圾分類與 LED 對照

| Class | 垃圾類別 | LED 顏色 | GPIO Pin |
|---|---|---|---|
| 0 | 寶特瓶 PET Bottle | 🟢 綠 | 12 |
| 1 | 鐵鋁罐 Aluminum Can | 🟡 黃 | 16 |
| 2 | 紙餐盒 Paper Container | 🔵 藍 | 20 |
| 3 | 塑膠袋 Plastic Bag | ⬜ 白 | 19 |
| 4 | 鋁箔包 Foil Package | 🟠 橘 | 23 |
| 5 | 一般垃圾 General Waste | 🔴 紅 | 21 |
| — | 蜂鳴器 Buzzer | — | 26 |

---

## 快速開始

```bash
make help   # 查看所有可用指令
make test   # 執行單元測試（不需硬體）
```

---

## 階段一：PC 開發與測試（Week 9–12）

### 1. 準備模型

PC 開發階段使用官方預訓練 YOLO26n（ultralytics 自動下載）：
```bash
mkdir -p models
# 不需手動下載，初次執行會自動抓取 yolo26n.pt
# 若要使用自訓練模型，將 best.pt 複製到 models/waste_classifier.pt
```

### 2. 執行單元測試

```bash
make test
# 或直接：python -m pytest tests/ -v
```

### 3. 啟動開發容器

```bash
# Linux（有 X11 預覽視窗）
xhost +local:docker
make dev

# Mac / Windows（無頭模式）
make dev-headless
```

啟動後可看到 MockGPIO 的 Console 輸出：
```
[MockGPIO] 💡  GREEN LED        HIGH
[MockGPIO] ⬛  GREEN LED        LOW
```

### 4. 進入容器除錯

```bash
make dev-shell            # bash shell
make dev-test-gpio        # 測試 MockGPIO 所有顏色循環
```

### 5. 熱重載開發

程式碼目錄已透過 volume 掛載，**修改 `.py` 檔案後直接重啟容器**即生效，不需重建映像：
```bash
docker-compose restart
```

---

## 階段二：資料收集 & 模型訓練（Week 10，在 PC / Colab）

### 1. 下載資料集

建議使用 TACO（含塑膠袋、鋁箔包，6 類完整覆蓋）：
```bash
# 需先至 https://roboflow.com 取得免費 API Key
make download-data KEY=YOUR_ROBOFLOW_KEY

# 或使用 Open Images V7（免登入，但鋁箔包較少）
docker-compose run --rm app python scripts/prepare_openimages.py
```

### 2. 訓練模型

```bash
# 使用 train.py（自動讀取 dataset/data.yaml，nc 與 config.py 保持同步）
make train

# 自訂參數
docker-compose run --rm app python train.py \
  --epochs 100 --batch 8 --model s
```

訓練完成後最佳模型自動複製至 `models/waste_classifier.pt`。

---

## 階段三：打包並部署至 Jetson（Week 11–13）

### 1. 將專案複製到 Jetson

```bash
# 在 PC 上打包（排除資料集與快取）
tar czf waste-sorting.tar.gz \
  --exclude='.git' --exclude='__pycache__' \
  --exclude='dataset' --exclude='runs' .

# 複製到 Jetson
scp waste-sorting.tar.gz user@jetson-ip:~/

# 在 Jetson 上解壓
ssh user@jetson-ip "tar xzf waste-sorting.tar.gz"
```

或直接 `git clone`（若有 git repo）。

### 2. 在 Jetson 上轉換 TensorRT engine（Week 11）

```bash
make jetson-build          # 建立 Jetson Docker 映像
make export-trt            # 轉換（需 5–15 分鐘）
# → 產生 models/waste_classifier.engine
```

### 3. 啟動 Jetson 容器

```bash
make jetson-up            # 背景常駐
make jetson-logs          # 追蹤即時 log
make jetson-shell         # 進入容器除錯
```

### 4. GPIO 硬體測試（Week 13 接線完成後）

```bash
make jetson-shell
python3 test_gpio.py                  # 完整 6 色循環
python3 test_gpio.py --led green      # 單色測試
python3 test_gpio.py --led orange     # 鋁箔包 LED
python3 test_gpio.py --buzzer-only    # 蜂鳴器
```

---

## GPIO 接線圖

```
Orin Nano GPIO       220Ω 限流電阻      LED
Pin 12  (Green)  ──── [ 220Ω ] ──── 綠 LED(+) ──── GND   寶特瓶
Pin 16  (Yellow) ──── [ 220Ω ] ──── 黃 LED(+) ──── GND   鐵鋁罐
Pin 20  (Blue)   ──── [ 220Ω ] ──── 藍 LED(+) ──── GND   紙餐盒
Pin 19  (White)  ──── [ 220Ω ] ──── 白 LED(+) ──── GND   塑膠袋
Pin 23  (Orange) ──── [ 220Ω ] ──── 橘 LED(+) ──── GND   鋁箔包
Pin 21  (Red)    ──── [ 220Ω ] ──── 紅 LED(+) ──── GND   一般垃圾
Pin 26  (Buzzer) ────────────────── Buzzer(+)  ──── GND
Pin 39/34 (GND)  ──── 所有 GND 共地
```

> 每顆 LED 電流 ≈ 10–15 mA，6 顆全亮 ≈ 90 mA，各 GPIO pin 最大 40 mA，不會超限。

---

## 設定調整（config.py / 環境變數）

| 環境變數 | 預設值 | 說明 |
|---|---|---|
| `ENV` | `dev` | `dev` = PC 模式，`jetson` = 部署模式 |
| `CONF_THRESH` | `0.60` | 低於此值觸發 fallback（一般垃圾） |
| `LED_DURATION` | `5.0` | 亮燈持續秒數 |
| `CAMERA_ID` | `0` | 攝影機索引 |
| `CAMERA_FLIP` | `0` | 攝影機翻轉（0=不翻轉, 2=上下） |
| `SHOW_PREVIEW` | `true` | 是否顯示預覽視窗 |

在 `docker-compose.yml` 的 `environment:` 區塊調整即可。

---

## 作者

- 李軒杰（I4A70）
- 黃義鈞（I4B58）

Edge AI 專題 | Capstone Project | 2026
