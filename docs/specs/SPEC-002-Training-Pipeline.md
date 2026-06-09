---
Title: Model Training Pipeline (Kaggle/Colab → ONNX → TensorRT → Jetson)
Date: 2026-05-30
Updated: 2026-06-09
ADR: ADR-001, ADR-002
---

## Goal
建立可重現的模型訓練與轉換 pipeline，從 Roboflow Waste Detection v1（42→5 class mapping）
fine-tune YOLO26m，轉換為 TensorRT FP16 engine，部署至 Jetson Orin Nano。

## Inputs
- Roboflow ProjectVerba YOLO Waste Detection v1（5,460 張，42 類，含真實 bbox）
- `train_kaggle.ipynb`：Kaggle T4 x2 訓練腳本（含 42→5 class mapping）
- `train_colab.ipynb`：Google Colab T4 訓練腳本（v5 備份）
- Roboflow API Key（儲存於 Kaggle/Colab Secrets，**不入 git**）

## Outputs
**訓練輸出（Kaggle/Colab）：**
- `runs/train/weights/best.pt`（PyTorch 模型，YOLO26m 5-class）
- `runs/train/results.csv`（訓練曲線）

**轉換輸出（在 Windows/Linux x86 執行，不可在 Jetson 上 export）：**
- `models/best_v6.onnx`（ONNX 格式）

**部署輸出（在 Jetson 上執行）：**
- `models/best_v6.engine`（TensorRT FP16，與 JetPack 版本綁定）

## Side Effects
- 訓練過程寫入 `runs/` 目錄（約 200–500 MB，不入 git）
- TensorRT 轉換在 Jetson 上需 10–20 分鐘（一次性，依 engine 版本）

## Edge Cases
| 場景 | 處理方式 |
|------|---------|
| 鐵鋁罐樣本過多（5,354 bbox） | copy_paste=0.3 + cls=0.3 緩解類別不平衡（v6） |
| mAP@50 < 0.70 | 增加 epochs 或調整 aug 參數後重訓 |
| TensorRT 轉換失敗 | 確認 ONNX opset 版本與 TensorRT 相容性 |
| Kaggle session 中斷 | 訓練有 patience=20 自動 early stop，checkpoint 自動儲存 |

## Done When
- [ ] `train_kaggle.ipynb` 完整執行，輸出 `best_v6.pt`（mAP@50 ≥ 0.755，超越 v5 基線）
- [ ] `data.yaml` 中 **5 類**標籤正確（寶特瓶/鐵鋁罐/紙餐盒/塑膠袋/一般垃圾），路徑有效
- [ ] 訓練 80 epochs（v6）後 val mAP@50 ≥ 0.755
- [ ] `best_v6.pt` 在 x86 機器匯出為 ONNX，SCP 至 Jetson
- [ ] Jetson 上 `trtexec` 轉換為 `.engine`，推論速度 ≥ 15 FPS（416×416 輸入）
- [ ] `accuracy_baseline.json` 更新為 v6 數值

## Rollback Plan
- 保留 `best_v5.engine`（mAP=0.755）作為生產備援，v6 驗證通過才替換
- 訓練中斷：Kaggle Output 面板下載 `best.pt` 後可繼續評估
- 若 v6 mAP 未超過 v5，繼續使用 v5 engine，不強制替換
