# ADR 合規檢查報告 — 2026-06-08

本文件記錄截至 2026-06-08 為止，所有實際操作與 ADR / SPEC 的合規狀況。

---

## ADR-001：模型選擇（YOLO + TensorRT FP16）

**原始決策**：使用 `yolo26s-seg.pt`（segmentation variant）

### 合規狀況：⚠️ 強制偏離

| 項目 | ADR 規定 | 實際狀態 | 影響 |
|------|---------|---------|------|
| 模型名稱 | `yolo26s-seg.pt` | `yolo11s.pt` | 強制偏離，yolo26s 不存在 |
| 任務類型 | segmentation（seg） | detection（detect） | 失去 instance mask 能力 |
| 輸入尺寸 | 416×416 | 416×416 | ✅ 符合 |
| 量化方式 | TensorRT FP16 | 尚未執行（待 Jetson） | 計畫中 |
| 信心門檻 | 0.45 | 0.45（config.py） | ✅ 符合 |
| 目標 FPS | ≥ 15 FPS | 尚未驗證 | 待測試 |

**偏離說明**：
- `yolo26s-seg.pt` 在 ultralytics 8.3.59 中不存在，為無效模型名稱
- 改用 `yolo11s.pt`（detection）作為可用的對應模型
- 失去 segmentation 能力，但 detect 模式對本專案垃圾分類任務已足夠

**建議後續行動**：
- 更新 ADR-001 說明此強制偏離及理由
- 若 ultralytics 未來釋出 yolo26s，評估是否升級

---

## ADR-002：資料集策略（三層資料）

**原始決策**：TACO（層1, ~1500張）+ TrashNet（層2, ~2527張）+ Roboflow自拍（層3, ~300張），合計約 3800 張

### 合規狀況：❌ 層1、層3 缺失

| 層 | 資料集 | ADR 目標 | 實際狀態 | 類別4影響 |
|----|-------|---------|---------|---------|
| 層1 | TACO（主力） | ~1500 張 | ❌ 未完成（正在處理） | 鋁箔包唯一來源 |
| 層2 | TrashNet | ~2527 張 | ✅ 完成（2527 張） | 無鋁箔包資料 |
| 層3 | Roboflow 自拍 | ~300 張 | ❌ 未開始 | — |

**關鍵缺口**：
- Class 4（鋁箔包）目前訓練資料為 **0 張**
- TrashNet 完全沒有 Tetra Pak / Foil Pak 類別
- 不修正將導致模型無法辨識鋁箔包

**各 Class 目前資料量**（僅 TrashNet）：

| Class | 類別 | 數量 | 是否達標 |
|-------|------|------|---------|
| 0 | 寶特瓶 | 225 | ⚠️ 偏低 |
| 1 | 鐵鋁罐 | 410 | ✅ |
| 2 | 紙餐盒 | 997 | ✅ |
| 3 | 塑膠袋 | 257 | ⚠️ 偏低 |
| 4 | 鋁箔包 | **0** | ❌ 嚴重缺失 |
| 5 | 一般垃圾 | 638 | ✅ |

**當前進行中工作**：
- Cell 6（TACO 下載 + 合併）正在準備執行
- TACO 含 `Drink carton` → 鋁箔包 mapping，補充後可改善 Class 4

---

## ADR-003：GPIO LED 致動設計

### 合規狀況：✅ 程式碼完全符合

| 項目 | ADR 規定 | 實際狀態 |
|------|---------|---------|
| GPIO 模式 | Board 編號 | ✅ `GPIO.setmode(GPIO.BOARD)` |
| 寶特瓶 Pin | 11（綠） | ✅ config.py Pin 11 |
| 鐵鋁罐 Pin | 13（黃） | ✅ config.py Pin 13 |
| 紙餐盒 Pin | 15（藍） | ✅ config.py Pin 15 |
| 塑膠袋 Pin | 19（白） | ✅ config.py Pin 19 |
| 鋁箔包 Pin | 21（橙） | ✅ config.py Pin 21 |
| 一般垃圾 Pin | 23（紅） | ✅ config.py Pin 23 |
| 蜂鳴器 Pin | 17 | ✅ config.py Pin 17 |
| LED 持續時間 | 5.0 秒 | ✅ `LED_DURATION = 5.0` |
| 蜂鳴器持續時間 | 0.2 秒 | ✅ `BUZZER_DURATION = 0.2` |
| Mock mode | GPIO import 失敗時自動降級 | ✅ try/except in gpio_controller.py |
| Fallback | 信心 < 0.45 → Pin 23（紅） | ✅ main.py 實作 |

**注意**：ADR-003 提到藍/白 LED 應改用 100Ω，config.py 的 comment 已標記，但接線時需確認實體電阻值。

---

## SPEC-001：全系統閉環

### 合規狀況：🔄 進行中

| Done When 條件 | 狀態 |
|--------------|------|
| `python src/main.py` 可在 Orin Nano 啟動 | ❌ 待執行 |
| 舉起寶特瓶，綠色 LED 500ms 內點亮 | ❌ 待硬體測試 |
| LED 5 秒後自動熄滅（誤差 ≤ 0.5s） | ❌ 待硬體測試 |
| 推論速度 ≥ 10 FPS | ❌ 待 TRT 轉換後測試 |
| logs/detections.csv 記錄結果 | ❌ 待執行 |
| 非 Jetson 環境自動 mock mode | ✅ gpio_controller.py 實作 |

---

## SPEC-002：訓練 Pipeline

### 合規狀況：🔄 進行中

| Done When 條件 | 狀態 |
|--------------|------|
| `prepare_taco.py` 執行成功 | ❌ 進行中（Cell 6） |
| 6 類標籤正確，路徑有效 | ✅ TrashNet 部分 |
| 訓練 50 epochs，val mAP@50 ≥ 0.70 | ❌ 尚未訓練 |
| best.pt 推論正確 | ❌ 尚未訓練 |
| Jetson .engine ≥ 15 FPS | ❌ 尚未轉換 |

---

## SPEC-003：GPIO 控制器模組

### 合規狀況：✅ 程式碼完成，待硬體驗證

| Done When 條件 | 狀態 |
|--------------|------|
| Jetson 上 Pin 11 點亮 5 秒 | ❌ 待硬體 |
| PC 上自動 mock mode | ✅ |
| 連續觸發 10 次無死鎖 | ❌ 待壓力測試 |
| cleanup() 後所有 pin 歸 LOW | ✅ 程式碼實作 |
| test_gpio.py 全部通過（mock mode） | ❌ 待執行 |

---

## 偏離摘要與建議行動

| 優先序 | 問題 | 建議行動 |
|--------|------|---------|
| 🔴 高 | Class 4（鋁箔包）= 0 張 | 立即執行 Cell 6（TACO 下載） |
| 🔴 高 | 訓練尚未開始 | Cell 6 完成後執行 Cell 7 |
| 🟡 中 | yolo26s→yolo11s 模型偏離 | 更新 ADR-001 說明強制偏離 |
| 🟡 中 | Roboflow 自拍（層3）未完成 | 硬體測試後補充自拍資料 |
| 🟢 低 | 藍/白 LED 電阻確認 | 接線時確認使用 100Ω |
