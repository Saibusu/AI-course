# 5-class 重構紀錄 — 2026-06-08

## 變更原因

鋁箔包（Foil/Tetra Pak）在 Roboflow ProjectVerba 資料集中樣本數不足，
訓練後精確率預期偏低。決定移除鋁箔包為獨立類別，改歸一般垃圾，系統縮減為 5-class。

## 類別變更對照

| 舊（6-class） | 新（5-class） |
|--------------|--------------|
| 0 寶特瓶 | 0 寶特瓶（不變）|
| 1 鐵鋁罐 | 1 鐵鋁罐（不變）|
| 2 紙餐盒 | 2 紙餐盒（不變）|
| 3 塑膠袋 | 3 塑膠袋（不變，但 LED pin 從 19 → 21）|
| 4 鋁箔包 | **移除** → 一般垃圾 |
| 5 一般垃圾 | 4 一般垃圾（ID 從 5 降為 4）|

## GPIO 針腳變更

| Pin | 舊用途 | 新用途 |
|-----|--------|--------|
| Pin 19 | 塑膠袋（停用）| **停用** |
| Pin 21 | 鋁箔包（橙色 220Ω）| **塑膠袋（白色 100Ω）** |
| Pin 23 | 一般垃圾（紅色）| 一般垃圾（不變）|

## 修改的檔案

| 檔案 | 修改內容 |
|------|---------|
| `src/config.py` | CLASS_NAMES 5-class；GPIO_PINS {3:21, 4:23}；LED_COLORS 移除 4 |
| `live_detect.py` | ENGINE_PATH → best_v5.engine；CLASS_NAMES/LABELS 確認 5-class |
| `train_colab.ipynb` Cell 0 | 類別表更新為 5-class，加 GPIO Pin 欄位 |
| `train_colab.ipynb` Cell 5 | TARGET_NAMES 5-class；NAME_MAP default → 4；out_dir → roboflow_5class |
| `train_colab.ipynb` Cell 6 | DATA_YAML → roboflow_5class/data.yaml |
| `docs/adr/ADR-003` | 針腳表更新，加變更說明 |

## 下一步

1. 確認麵包板接線：塑膠袋 LED 移至 Pin 21（白色 100Ω）
2. 執行 Colab train_colab.ipynb（Cell 1 → 7）
3. 訓練完成後：Windows ONNX export → SCP → Jetson trtexec → live_detect.py 測試
