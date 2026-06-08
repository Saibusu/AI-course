# Jetson 推論修復紀錄 — 2026-06-08

## 問題根因確認

### PyTorch / ultralytics 推論 Crash
- Jetson PyTorch 版本：`2.5.0a0+872d972e41.nv24.08`（NVIDIA JetPack 自製 build）
- ultralytics 8.4.61 + PyTorch 2.5.0a0 在 aarch64 上執行推論時 crash
- 錯誤：`stl_vector.h:1130 Assertion '__n < this->size()' failed. Aborted (core dumped)`
- 影響：所有 ultralytics 推論、onnxruntime 推論皆 crash

### 解決路徑

| 嘗試方案 | 結果 |
|---------|------|
| ultralytics YOLO11 直接推論 | ❌ C++ crash |
| ultralytics YOLO26 直接推論 | ❌ C++ crash |
| onnxruntime ONNX 推論 | ❌ 同樣 C++ crash |
| OpenCV DNN + YOLO11 ONNX | ✅ 成功 |
| OpenCV DNN + YOLO26 ONNX | ❌ `TopK` operator 不支援 |
| ultralytics + TRT engine | ❌ 前後處理仍走 PyTorch |
| **pycuda + TRT engine** | ✅ **成功，完全繞過 PyTorch** |

### 最終可行方案
```
訓練（Colab）→ ONNX 匯出（Windows）→ trtexec 轉換（Jetson）→ pycuda 推論（Jetson）
```

## 模型訓練歷程

| 版本 | 架構 | 資料集 | mAP@50 | 問題 |
|------|------|--------|--------|------|
| best.pt (v1) | yolo11s | TrashNet only | 0.795 | 全圖 bbox，無法真實偵測 |
| best_v2.pt | yolo11m | TrashNet+TACO | 0.794 | 同上 + TACO 標注雜訊 |
| best_v3.pt | yolo26s | merged_v3 | 0.439 | TACO 一般垃圾標注噪音嚴重 |
| best_v4.pt | yolo26m | TrashNet 5-class | 0.805 | 全圖 bbox（根本問題未解） |

### TrashNet 全圖 bbox 問題
`prepare_trashnet.py` 將 TrashNet（分類資料集）轉換為 YOLO 時，
所有標注都寫成 `cls 0.5 0.5 1.0 1.0`（全圖覆蓋）。
模型只學到「物件填滿畫面時才偵測」，無法在真實場景中定位物件。

## Jetson 部署現況

### 可用檔案
```
~/AI-course/models/
  best.pt       # yolo11s，不可用（PyTorch crash）
  best_v2.pt    # yolo11m，不可用（PyTorch crash）
  best.onnx     # yolo11s ONNX，OpenCV DNN 可用
  best_v2.onnx  # yolo11m ONNX，OpenCV DNN 可用
  best_v4.onnx  # yolo26m ONNX，OpenCV DNN 不支援 TopK
  best_v4.engine # yolo26m TRT FP16，pycuda 可用 ✅
```

### 執行方式
```bash
cd ~/AI-course
python live_detect.py  # 使用 best_v4.engine + pycuda
```

### live_detect.py 架構
- 推論：pycuda + TRT engine（無 PyTorch 依賴）
- 攝影機：GStreamer nvarguscamerasrc（CSI）
- 顯示：GStreamer autovideosink（HDMI）
- 後處理：numpy（不依賴 ultralytics）
- TRT 輸出格式：(1, 300, 6) → [x1,y1,x2,y2,conf,cls_id]

## 下一步：重新訓練（換資料集）

### 問題
現有訓練資料（TrashNet）全圖 bbox，導致模型無法在真實場景中偵測物件。

### 選定資料集
**YOLO Waste Detection (ProjectVerba)** — Roboflow Universe
- 5,460 張（+增強後可能更多）
- 42 類別，含真實 bounding box
- 支援 YOLO26 格式直接下載
- CC BY 4.0 授權

### 類別對應（42 → 6）
| 目標類別 | 對應原始類別 |
|---------|------------|
| 寶特瓶(0) | Plastic bottle, Milk bottle, Plastic can |
| 鐵鋁罐(1) | Aluminum can, Tin |
| 紙餐盒(2) | Paper, Cardboard, Paper cups, Disposable tableware |
| 塑膠袋(3) | Plastic bag, Zip plastic bag, Stretch film |
| 鋁箔包(4) | Foil, Tetra pack |
| 一般垃圾(5) | 其餘所有類別 |

### 訓練計畫
- 架構：yolo26m.pt（detection，非 seg，因資料集只有 bbox）
- 訓練平台：Colab T4
- 部署流程：ONNX → trtexec → best_v5.engine → pycuda
