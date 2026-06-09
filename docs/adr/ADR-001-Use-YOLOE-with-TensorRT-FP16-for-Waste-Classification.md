---
Title: Use YOLO26m with TensorRT FP16 + pycuda for Waste Classification
Date: 2026-05-30
Updated: 2026-06-09
Status: Accepted
Accepted-by: 李軒杰 (2026-06-09)
---

> **變更說明（2026-06-09）**：實機驗證後發現兩項強制偏離，已更新本 ADR 反映實際部署狀態。
> 偏離一：模型由 `yolo26s-seg` 改為 `yolo26m`（detect variant）。
> 偏離二：推論框架由 ultralytics 改為 pycuda，原因為 Jetson PyTorch crash（見下方 Consequences）。

## Context

本專案需要在 Jetson Orin Nano（8 GB RAM、25W TDP）上進行即時垃圾分類，
辨識 **5 類**垃圾（寶特瓶、鐵鋁罐、紙餐盒、塑膠袋、一般垃圾）。
推論延遲目標：< 100ms（≥ 10 FPS）以維持流暢的使用者體驗。

YOLO26 為 Ultralytics 官方發布的最新世代模型，支援 detect / seg / cls / pose / obb
五大任務。在 Orin Nano 上搭配 TensorRT FP16 可達到 ≥ 15 FPS（416×416 輸入）。

**Jetson 推論環境限制（Week 13 實機驗證確認）：**
Jetson JetPack 內建 PyTorch `2.5.0a0+nv24.08`（NVIDIA 自製 build），
在 aarch64 執行 ultralytics 推論時發生 C++ assertion crash：
```
stl_vector.h:1130: Assertion '__n < this->size()' failed. Aborted (core dumped)
```
所有經過 PyTorch/ultralytics 的推論路徑（含 ONNX Runtime）均受影響。
唯一可行方案：直接使用 pycuda 操作 TensorRT engine，完全繞過 PyTorch。

## Decision

**使用 `yolo26m.pt`（medium, detection variant）作為基底模型進行 fine-tune，
以 trtexec 轉換為 TensorRT FP16 engine，並以純 pycuda 進行推論。**

具體參數：
- 模型：`yolo26m.pt`（medium detection variant，訓練精度優於 yolo26s）
- 輸入解析度：416 × 416
- 量化：TensorRT FP16（`trtexec --onnx=best_v5.onnx --saveEngine=best_v5.engine --fp16`）
- 推論框架：**pycuda + TensorRT Runtime**（完全不使用 PyTorch / ultralytics）
- 目標 FPS：≥ 10 FPS on Orin Nano（實測 ~15 FPS）
- 信心門檻：0.55（低於此值 fallback 至「一般垃圾」class 4）

**部署 Pipeline：**
```
Kaggle/Colab 訓練(yolo26m) → ONNX 匯出(Windows) → SCP to Jetson
→ trtexec → best_v5.engine → live_detect.py (pycuda)
```

## Consequences

**正面：**
- YOLO26m detection 在同等計算量下精度優於 yolo26s
- pycuda 完全繞過 PyTorch，不受 JetPack PyTorch crash 影響
- TRT FP16 速度 ~2× FP32，記憶體減半，符合 Orin Nano 限制
- 推論延遲實測 ~20ms/frame，遠低於 100ms 目標

**負面 / 風險（已知）：**
- pycuda 手動管理 CUDA buffer（HtoD / execute / DtoH），程式碼複雜度提升
- ONNX 匯出需在 Windows/Linux x86 上執行（不能在 Jetson 執行 ultralytics export）
- TRT engine 與 JetPack 版本綁定，升級 JetPack 需重新 trtexec

**後續工作：**
- ADR-002：資料集策略
- 詳細記錄：`docs/progress/2026-06-08-jetson-inference-fix.md`

## Alternatives Considered

### Option A — YOLOv8n（前世代標準版）
輕量，API 成熟，但性能低於 YOLO26，且非最新世代。
**未選原因：既然 YOLO26 已在 Ultralytics 官方支援，無理由退回舊世代。**

### Option B — OpenCV DNN + YOLO26 ONNX
OpenCV DNN 不依賴 PyTorch，理論上可繞過 crash。
**未選原因：YOLO26 輸出層使用 TopK operator，OpenCV DNN 4.x 不支援，實測失敗。**

### Option C — MobileNetV3 + SSD（純分類）
推論速度最快，但無偵測能力，遮擋時準確率大幅下降。
**未選原因：遮擋場景表現差，且缺少 bounding box 定位能力。**
