---
Title: Dataset Strategy — TACO + TrashNet + Roboflow Custom 6-Class Mapping
Date: 2026-05-30
Status: Accepted
Accepted-by: Human (2026-05-30)
---

## Context

本系統需辨識台灣公共場所常見的 6 類垃圾：
1. 寶特瓶（PET bottle）
2. 鐵鋁罐（Metal can）
3. 紙餐盒（Paper food container）
4. 塑膠袋（Plastic bag）
5. 鋁箔包（Foil/Tetra Pak）
6. 一般垃圾（General waste）

公開資料集（TACO、TrashNet）的類別定義與本專案不完全一致，
需要制定明確的 mapping 策略與補充自拍資料的計畫。
人類決策：採用三層資料策略，並加入 TrashNet（Option A）作為第二層補充。

## Decision

**三層資料策略（含 TrashNet）：**

### 層 1：TACO Dataset（主力，~1500 張）
來源：https://github.com/pedropro/TACO（COCO 格式）

TACO → 本專案 6 類 Mapping：
| TACO 類別 | 本專案類別 |
|-----------|-----------|
| Drink carton | 鋁箔包 |
| Bottle cap, Bottle | 寶特瓶 |
| Can, Aerosol | 鐵鋁罐 |
| Paper cup, Carton, Meal carton | 紙餐盒 |
| Plastic bag & wrapper, Six pack rings | 塑膠袋 |
| 其餘所有類別 | 一般垃圾 |

### 層 2：TrashNet（補充分類，~2527 張）
來源：https://github.com/garythung/trashnet（分類格式，6 大類資料夾）

TrashNet → 本專案 6 類 Mapping：
| TrashNet 資料夾 | 本專案類別 |
|----------------|-----------|
| plastic/ | 寶特瓶（0）+ 塑膠袋（3）→ 各 50% 分配 |
| metal/ | 鐵鋁罐（1）|
| paper/ | 紙餐盒（2）|
| cardboard/ | 紙餐盒（2）|
| glass/ | 一般垃圾（5）|
| trash/ | 一般垃圾（5）|

注意：TrashNet 為分類資料集（無 bbox），需以全圖 bbox 轉換為 YOLO detect 格式。
指令：`python data/prepare_trashnet.py`

### 層 3：Roboflow 補充自拍（約 300 張）
- 在實際部署場景（室內、螢光燈）下拍攝
- 每類至少 50 張，涵蓋：正面、斜角、手持、桌放
- Roboflow 標註 + 資料增強（翻轉/旋轉 ±15°/亮度 ±30%/高斯噪點）
- 匯出格式：YOLOv8 格式（含 data.yaml）

**資料分割（合併後）：**
- Train : Val : Test = 70 : 20 : 10
- 確保每類在 Val/Test 均有代表性樣本
- 預估總數：TACO ~1500 + TrashNet ~2000 + 自拍 ~300 = **約 3800 張**

## Consequences

**正面：**
- TACO 提供真實場景（戶外、餐廳），TrashNet 提供大量乾淨分類樣本
- 三層互補：場景多樣性、類別平衡性、台灣特定容器
- Mapping 策略明確，可重現

**負面 / 風險：**
- TrashNet 為白底（實驗室環境），domain gap 存在，需在 val 集監控
- plastic/ 資料夾同時 mapping 到寶特瓶和塑膠袋，標籤噪音較高
- 合併三層資料需確認 data.yaml 路徑正確，避免資料洩漏至 val/test

**後續工作：**
- `data/prepare_taco.py`：TACO 轉換腳本
- `data/prepare_trashnet.py`：TrashNet 轉換腳本
- `data/merge_datasets.py`：三層資料合併與分割

## Alternatives Considered

### Option A — 純 TrashNet
已納入作為層 2 補充，而非主力。
**未選為主力原因：白底影像 domain gap 過大，獨立使用時遷移效果不佳。**

### Option B — 完全自拍
8 週內無法收集足夠多樣資料（目標 3800 張以上）。
**未選原因：時間與資源不足以支撐全自拍策略。**
