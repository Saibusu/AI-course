---
Title: Use YOLO26 with TensorRT FP16 for Waste Classification
Date: 2026-05-30
Status: Accepted
Accepted-by: Human (2026-05-30)
---

## Context

本專案需要在 Jetson Orin Nano（8 GB RAM、25W TDP）上進行即時垃圾分類，
辨識 6 類垃圾（寶特瓶、鐵鋁罐、紙餐盒、塑膠袋、鋁箔包、一般垃圾）。
推論延遲目標：< 100ms（≥ 10 FPS）以維持流暢的使用者體驗。

YOLO26 為 Ultralytics 官方發布的最新世代模型，支援 detect / seg / cls / pose / obb
五大任務，model file 命名規範為 `yolo26{n|s|m|l|x}[-seg|-cls|-pose|-obb].pt`。
在 Orin Nano 上搭配 TensorRT FP16 可達到 ≥ 15 FPS（416×416 輸入）。

## Decision

**使用 `yolo26s-seg.pt`（small, segmentation variant）作為基底模型進行 fine-tune，
搭配 TensorRT FP16 量化後部署至 Jetson Orin Nano。**

具體參數：
- 模型：`yolo26s-seg.pt`（small segment variant）
- 輸入解析度：416 × 416
- 量化：TensorRT FP16（`model.export(format="engine", half=True)`）
- 推論框架：Ultralytics + TensorRT engine（`.engine` 格式）
- 目標 FPS：≥ 15 FPS on Orin Nano
- 信心門檻：0.45（低於此值 fallback 至「一般垃圾」）

安裝：`pip install ultralytics`（含 YOLO26 支援）

## Consequences

**正面：**
- YOLO26 為 Ultralytics 官方最新世代，性能優於 YOLOv8/YOLO11
- TensorRT FP16 在 Orin Nano 上已有大量實作先例
- Ultralytics API 統一（`YOLO("yolo26s-seg.pt")`），訓練→轉換→推論一致
- seg variant 提供 instance segmentation mask，遮擋場景更健壯

**負面 / 風險：**
- YOLO26 較新，若 ultralytics 版本過舊需升級（`pip install -U ultralytics`）
- TensorRT 版本與 JetPack 相容性需實機驗證（risk: Week 11）
- small model mAP 可能在極端光線下偏低，可升級至 `yolo26m-seg.pt` 若不足

**後續工作：**
- ADR-002：資料集策略
- SPEC-002：訓練 pipeline 細節

## Alternatives Considered

### Option A — YOLOv8n（前世代標準版）
輕量，API 成熟，但性能低於 YOLO26，且非最新世代。
**未選原因：既然 YOLO26 已在 Ultralytics 官方支援，無理由退回舊世代。**

### Option B — MobileNetV3 + SSD（純分類）
推論速度最快，但無 segmentation，遮擋時準確率大幅下降。
且需要完全自訓，無 pretrained weights 可利用。
**未選原因：遮擋場景表現差，且缺少 instance segmentation 能力。**
