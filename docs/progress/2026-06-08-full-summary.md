# 完整操作紀錄與決策總覽 — 2026-06-08

本文件彙整 2026-06-08 所有訓練實驗、架構決策、問題排除，供期末報告使用。

---

## 一、分支策略

| 分支 | 用途 | 狀態 |
|------|------|------|
| `main` | YOLO11 實驗記錄（v1~v3），保留做比較基準 | 封存，不繼續開發 |
| `feature/yolo26` | YOLO26 主線（ADR-001 對齊），v4 訓練目標 | **目前主線** |

---

## 二、訓練版本總覽

| 版本 | 模型 | 資料集 | 類別數 | mAP@50 | 狀態 |
|------|------|--------|--------|--------|------|
| v1 | yolo11s | TrashNet（2533 張） | 6 | **0.795** | ✅ 完成 |
| v2 | yolo11m | TrashNet（2533 張） | 6 | **0.794** | ✅ 完成（持平，大模型無效）|
| v3（yolo26-first） | yolo26s | merged_v3（3140 張，含 TACO） | 6 | **0.439** | ❌ TACO 雜訊毒化 |
| **v4（進行中）** | **yolo26m** | **trashnet_5class（2527 張）** | **5** | **TBD** | 🔄 訓練中 |

---

## 三、決策紀錄

### 決策 1：模型從 YOLO11 回歸 YOLO26（2026-06-08）

**觸發**：ASP Review 發現 `main` 分支 notebook 使用 `yolo11m`，違反 ADR-001（規定 `yolo26s-seg.pt`）。

**決定**：建立 `feature/yolo26` 分支，回歸 ADR-001。

**技術發現**：
- ultralytics 8.4.61 已正式支援 YOLO26（`yolo26s.pt`、`yolo26m.pt` 均可下載）
- `yolo26s-seg.pt` 為 segmentation variant，需要 polygon mask 標註才能訓練
- 目前訓練資料為 bounding box 格式 → 改用 `yolo26s.pt` / `yolo26m.pt`（detect variant）

---

### 決策 2：捨棄 TACO 資料集（2026-06-08）

**觸發**：v3 訓練結果 mAP@50 = 0.439，遠低於 v1（0.795）。

**診斷**：
- TACO 轉換後，Class 5（一般垃圾）有 **3734 instances**，標籤極為雜亂
- val mAP 一般垃圾 = 0.258（311 張 val，786 instances，卻幾乎無法辨識）
- 加入 TACO → 模型學到的「一般垃圾」特徵混亂，連帶拖垮其他類別

**決定**：v4 起完全捨棄 TACO，回到 TrashNet only。

---

### 決策 3：移除鋁箔包類別，從 6 類縮減為 5 類（2026-06-08）

**觸發**：TACO 下載問題（Flickr 失效）→ Zenodo 備份雖可下載，但 TACO 標籤品質問題導致整體 mAP 崩潰。

**類別對照**：

| 原始（6 類） | v4（5 類） | 說明 |
|------------|-----------|------|
| 0 寶特瓶 | 0 寶特瓶 | 不變 |
| 1 鐵鋁罐 | 1 鐵鋁罐 | 不變 |
| 2 紙餐盒 | 2 紙餐盒 | 不變 |
| 3 塑膠袋 | 3 塑膠袋 | 不變 |
| 4 鋁箔包 | **刪除** | 組員補充後恢復 |
| 5 一般垃圾 | **4 一般垃圾** | Class ID 5→4 |

**影響**：
- GPIO 映射需同步調整（config.py 待更新）
- 期末報告說明：5 類版本為暫行版，組員補充鋁箔包資料後升級為 6 類

---

## 四、問題排除紀錄

| 問題 | 原因 | 解法 |
|------|------|------|
| `PIL._Ink ImportError` | `pip install -U Pillow` 升版後 Colab 記憶體殘留舊版 | Runtime → 重新啟動工作階段；或不升級 Pillow |
| `yolo26s-seg.pt` RuntimeError | Seg 模型訓練需要 polygon mask，我們只有 bbox | 改用 `yolo26s.pt` / `yolo26m.pt`（detect variant）|
| `SameFileError`（Cell 8） | glob 找到根目錄的 `best.pt`，自我複製 | 用 `next((p for p in pts if 'name' in p), None)` 過濾 |
| TACO Flickr 下載（僅 6 張） | Flickr 已限制 TACO 圖片存取 | Zenodo 官方備份（DOI: 10.5281/zenodo.3587843）|
| TACO 加入後 mAP 崩潰（0.439） | 一般垃圾標籤雜亂（3734 instances，多類 TACO 類別混入）| 捨棄 TACO，改 5 類系統 |

---

## 五、各訓練詳細結果

### v1：yolo11s + TrashNet（mAP = 0.795）

| Class | 類別 | mAP@50 |
|-------|------|--------|
| 0 | 寶特瓶 | 0.426 ⚠️ |
| 1 | 鐵鋁罐 | 0.963 ✅ |
| 2 | 紙餐盒 | 0.991 ✅ |
| 3 | 塑膠袋 | 0.660 ⚠️ |
| 4 | 鋁箔包 | N/A ❌ |
| 5 | 一般垃圾 | 0.936 ✅ |
| **all** | | **0.795** |

### v2：yolo11m + TrashNet（mAP = 0.794）

結論：換更大模型無效，資料量才是瓶頸。與 v1 幾乎持平。

### v3：yolo26s + merged_v3（mAP = 0.439）❌

| Class | 類別 | mAP@50 | 備註 |
|-------|------|--------|------|
| 0 | 寶特瓶 | 0.261 | 嚴重下降 |
| 1 | 鐵鋁罐 | 0.708 | 尚可 |
| 2 | 紙餐盒 | 0.935 | 維持 |
| 3 | 塑膠袋 | 0.462 | 下降 |
| 4 | 鋁箔包 | 0.010 | 幾乎無效（11 val images）|
| 5 | 一般垃圾 | 0.258 | TACO 雜訊主因 |
| **all** | | **0.439** | |

---

## 六、v4 訓練參數

| 參數 | 值 | 說明 |
|------|-----|------|
| 模型 | `yolo26m.pt` | YOLO26 medium，ADR-001 世代 |
| 資料集 | `trashnet_5class` | TrashNet 重標，5 類 |
| 張數 | 2527 張（train 約 2100） | |
| epochs | 100 | 比 v1/v2 更充分 |
| imgsz | 640 | 比 v1/v2 高解析度 |
| batch | 8 | T4 顯存限制 |
| cos_lr | True | Cosine LR schedule |
| mixup | 0.1 | 額外資料增強 |
| 預期 mAP | ≥ 0.80 | 目標 |

---

## 七、程式碼異動清單

| 檔案 | 異動內容 |
|------|---------|
| `train_colab.ipynb` | 完整重構：Cell 5b 新增（5-class 轉換）、Cell 7/8 更新至 v4 |
| `docs/progress/2026-06-08-yolo26-branch.md` | 建立 feature/yolo26 決策紀錄 |
| `docs/progress/2026-06-08-full-summary.md` | 本文件 |
| `data/prepare_taco.py` | 路徑 fallback 修正（先前）|
| `data/prepare_roboflow_drink.py` | 新增（備用轉換腳本）|
| `.gitignore` | 封鎖所有 `.pt`、`.engine`、`models/`、`runs/` |

---

## 八、待辦事項

- [ ] v4 訓練完成，記錄 mAP@50（各 class）
- [ ] 比較 v1（yolo11s）vs v4（yolo26m）同資料集下的差異
- [ ] 若 v4 mAP ≥ 0.80 → 執行 Cell 8，下載 `best_v4.pt`
- [ ] SCP 傳至 Jetson：`scp best_v4.pt jetson@<IP>:~/AI-course/models/best.pt`
- [ ] 更新 `src/config.py`：CLASS_NAMES 和 GPIO_PINS 改為 5 類
- [ ] Jetson TensorRT 轉換：`python src/main.py --export-trt`
- [ ] 硬體接線（LED × 5 + 蜂鳴器）
- [ ] 系統整合測試
- [ ] 組員補充鋁箔包資料 → 第五輪訓練（6 類恢復）
