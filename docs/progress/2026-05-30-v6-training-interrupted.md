# Training Log — v6 (Interrupted at Epoch 72/80)

**Date**: 2026-05-30
**Platform**: Kaggle (GPU T4 x2)
**Notebook**: `train_kaggle.ipynb`
**Model base**: `yolo26m.pt`
**Dataset**: YOLO Waste Detection (ProjectVerba, Roboflow) — 5,460 張，42 類 → 5 類 mapping
**Output weight**: `best_v6.pt` / `best_v6.onnx`

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

## 停止原因

使用者手動中斷（Kaggle Cancel Run）。
mAP 在 epoch 68–71 趨於穩定（0.720–0.722），判斷收斂，
繼續 8 個 epoch 提升空間有限。

---

## 後續動作

停止後在 Kaggle 執行 Cell 7（Export ONNX）：
```python
from ultralytics import YOLO
model = YOLO('/kaggle/working/best_v6.pt')
model.export(format='onnx', imgsz=416, simplify=True, opset=12)
```

然後下載：
- `/kaggle/working/best_v6.pt`
- `/kaggle/working/best_v6.onnx`

放入本專案 `models/` 後，在 Jetson 執行：
```bash
/usr/src/tensorrt/bin/trtexec \
  --onnx=models/best_v6.onnx \
  --saveEngine=models/best_v6.engine \
  --fp16
```

---

## 與 v5 比較

| 版本 | mAP@50 | 狀態 |
|------|--------|------|
| v5   | 0.755  | 已部署 (best_v5.engine) |
| v6   | ~0.721 | 中斷於 epoch 72，未超越 v5 |

> **結論**：v6 目前未超越 v5（0.755）。
> 若 v6 ONNX 匯出後在 Jetson 實測 mAP 接近 v5，可視需求決定是否替換。
> 建議保留 v5 engine 繼續作為 production 版本。
