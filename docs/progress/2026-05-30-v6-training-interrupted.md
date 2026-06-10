# Training Log — v6 (ABORTED — Kernel crashed on Cancel)

**Date**: 2026-05-30
**Platform**: Kaggle (GPU T4 x2)
**Notebook**: `train_kaggle.ipynb`
**Model base**: `yolo26m.pt`
**Dataset**: YOLO Waste Detection (ProjectVerba, Roboflow) — 5,460 張，42 類 → 5 類 mapping
**Output weight**: ❌ 未取得（Kernel crash，Cell 7 ONNX 匯出未執行）

> **結果：v6 訓練作廢。** Cancel Run 後 Kaggle Kernel 崩潰，無法執行 Cell 7 匯出 ONNX，
> `best_v6.pt` 無法下載。**繼續使用 v5（mAP=0.755）作為 production 模型。**

---

## 訓練參數

| 參數 | 值 |
|------|-----|
| epochs | 80（中途停止於 72） |
| imgsz | 416 |
| batch | 16 |
| device | GPU T4 x2 |
| nc | 5 |

---

## 截止 Epoch 72 的指標（從 Kaggle 畫面擷取）

| Epoch | GPU Mem | box_loss | cls_loss | dfl_loss | mAP@50 | mAP@50-95 |
|-------|---------|----------|----------|----------|--------|-----------|
| 68/80 | 8.93G   | 0.8225   | 0.4481   | 0.01596  | 0.722  | 0.500     |
| 69/80 | 8.88G   | 0.8135   | 0.4403   | 0.01598  | 0.720  | 0.498     |
| 70/80 | 8.95G   | 0.8054   | 0.4424   | 0.01574  | 0.721  | 0.499     |
| 71/80 | 8.93G   | 0.6476   | 0.1869   | 0.01596  | 0.721  | 0.498     |
| 72/80 | 8.94G   | 0.6234   | 0.1658   | 0.01504  | —（中斷）| — |

**Instances**: 1559（val set）
**Val Images**: 1092

---

## 停止原因與崩潰記錄

使用者手動點擊 Cancel Run（epoch 72/80）→ Kaggle Kernel 崩潰，
Cell 7（ONNX 匯出）無法執行，`best_v6.pt` 及 `best_v6.onnx` 均未成功下載。

## 後續動作（若要重跑 v6）

重開一個新的 Kaggle session，執行 `train_kaggle.ipynb` Cell 1–7 全部跑完，
**不要在訓練中途 Cancel**，等訓練完成後直接在同一 session 執行 Cell 7 匯出。

或改用 Colab（`train_colab.ipynb`），Colab 崩潰風險較低，但 GPU 時間有限。

---

## 與 v5 比較

| 版本 | mAP@50 | 狀態 |
|------|--------|------|
| v5   | 0.755  | 已部署 (best_v5.engine) |
| v6   | ~0.721 | 中斷於 epoch 72，未超越 v5 |

> **結論**：v6 目前未超越 v5（0.755）。
> 若 v6 ONNX 匯出後在 Jetson 實測 mAP 接近 v5，可視需求決定是否替換。
> 建議保留 v5 engine 繼續作為 production 版本。
