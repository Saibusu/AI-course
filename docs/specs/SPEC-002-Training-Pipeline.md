---
Title: Model Training Pipeline (PC/Colab → ONNX → TensorRT → Jetson)
Date: 2026-05-30
ADR: ADR-001, ADR-002
---

## Goal
建立可重現的模型訓練與轉換 pipeline，從 TACO + 自拍資料訓練 YOLOE-11s，
轉換為 TensorRT FP16 engine，部署至 Jetson Orin Nano。

## Inputs
- TACO dataset（COCO JSON 格式，~1500 張）
- Roboflow 自拍資料（YOLOv8 格式，~300 張）
- `data/data.yaml`：6 類定義檔
- `data/prepare_taco.py`：TACO → YOLO 格式轉換腳本

## Outputs
**訓練輸出：**
- `runs/train/weights/best.pt`（PyTorch 模型）
- `runs/train/results.csv`（訓練曲線）
- `runs/train/val_batch*.jpg`（驗證視覺化）

**轉換輸出（在 Jetson 上執行）：**
- `models/waste_sorter.onnx`
- `models/waste_sorter_fp16.engine`

## Side Effects
- 訓練過程寫入 `runs/` 目錄（約 200–500 MB）
- TensorRT 轉換在 Jetson 上需 10–20 分鐘（一次性）

## Edge Cases
| 場景 | 處理方式 |
|------|---------|
| 某類別樣本數 < 30 | 增加 Roboflow 資料增強倍率至 5x |
| mAP@50 < 0.70 | 增加 epochs（50→100）並調整 conf_thres |
| TensorRT 轉換失敗 | 降級使用 ONNX Runtime 推論 |
| Colab 訓練中斷 | 使用 `resume=True` 從最後 checkpoint 繼續 |

## Done When
- [ ] `python data/prepare_taco.py` 執行成功，輸出 6 類 YOLO 格式資料
- [ ] `data.yaml` 中 6 類標籤正確，路徑有效
- [ ] 訓練 50 epochs 後 val mAP@50 ≥ 0.70
- [ ] `best.pt` 可在 PC 上用 Ultralytics 推論，對測試圖片輸出正確類別
- [ ] Jetson 上 `.engine` 推論速度 ≥ 15 FPS（416×416 輸入）
- [ ] ONNX 轉換無 warning（除 opset 版本提示外）

## Rollback Plan
- 訓練：保留 `last.pt` 與 `best.pt`，可隨時回退至任意 checkpoint
- 轉換失敗：`main.py` 自動 fallback 至 `best.pt`（PyTorch 模式）
- 若 mAP 不足：增加自拍資料後重訓，不修改 TACO mapping
