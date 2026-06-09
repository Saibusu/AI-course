---
Title: Dataset Strategy — Roboflow 5-Class Mapping (42→5 classes)
Date: 2026-05-30
Updated: 2026-06-09
Status: Accepted
Accepted-by: 李軒杰 (2026-06-09)
---

> **變更說明（2026-06-09）**：原三層策略（TACO+TrashNet+自拍）在實作中發現根本性缺陷，
> 已全面切換為 Roboflow 公開資料集。系統同步由 6-class 縮減為 5-class（移除鋁箔包）。
> 詳細決策歷程保留於「廢棄策略」一節。

## Context

本系統需辨識台灣公共場所常見的 **5 類**垃圾（2026-06-08 更新，移除鋁箔包）：
1. 寶特瓶（PET bottle）
2. 鐵鋁罐（Metal can）
3. 紙餐盒（Paper food container）
4. 塑膠袋（Plastic bag）
5. 一般垃圾（General waste）

**鋁箔包移除原因：**
Roboflow 資料集中 foil/tetra pack 類別 bbox 數量接近 0，無法訓練有效分類器。
加上鋁箔包外觀與紙餐盒高度相似，強行納入只會降低整體精度。
決策：鋁箔包歸入一般垃圾（class 4）。

## Decision

**使用 Roboflow ProjectVerba YOLO Waste Detection v1，進行 42→5 class mapping。**

### 資料集來源
- 平台：Roboflow（workspace: projectverba, project: yolo-waste-detection, version: 1）
- 格式：yolo26（YOLO format，含真實 bounding box）
- 總張數：**5,460 張**
- 原始類別數：42 類

### 42 → 5 Class Mapping

| 原始類別（Roboflow）| 本專案類別 |
|-------------------|---------|
| plastic bottle, milk bottle, plastic can, plastic canister, plastic cup | 0 寶特瓶 |
| aluminum can, tin, scrap metal, aerosols, food can, drink can, iron utensils | 1 鐵鋁罐 |
| paper, cardboard, paper cups, paper cup, paper bag, disposable tableware, papier mache, paper shavings, cellulose | 2 紙餐盒 |
| plastic bag, zip plastic bag, stretch film, combined plastic, plastic film | 3 塑膠袋 |
| 其餘所有類別（含 foil, glass, wood, ceramic 等）| 4 一般垃圾 |

### 訓練資料分佈（mapping 後）
| 類別 | bbox 數量 | 備註 |
|------|---------|------|
| 寶特瓶 | 4,039 | |
| 鐵鋁罐 | 5,354 | 最多，v6 用 copy_paste 平衡 |
| 紙餐盒 | 2,170 | |
| 塑膠袋 | 2,279 | |
| 一般垃圾 | 5,078 | |

### 訓練設定（v5 已部署 / v6 進行中）

**v5（已部署，mAP@50=0.755）：**
- 平台：Google Colab T4
- epochs=35, patience=10, batch=16, imgsz=640
- 訓練腳本：`train_colab.ipynb`

**v6（訓練中，Kaggle T4 x2）：**
- epochs=80, patience=20, copy_paste=0.3, cls=0.3（改善類別不平衡）
- 訓練腳本：`train_kaggle.ipynb`

### Mapping 腳本
```python
# train_kaggle.ipynb Cell 5
# 42 原始類別 → 5 目標類別
NAME_MAP = {
    'plastic bottle': 0, 'aluminum can': 1, 'paper': 2,
    'plastic bag': 3,  # ... 共 25 個具名對應
    # 其餘 default → 4 一般垃圾
}
```

## Consequences

**正面：**
- 真實 bounding box（非全圖框），模型可學習物件定位
- 5,460 張覆蓋多種場景（室內、戶外、不同光線）
- Roboflow API 下載可重現（workspace/project/version 固定）
- 42 類 mapping 覆蓋大多數真實垃圾類型

**負面 / 風險：**
- 鐵鋁罐樣本最多（5,354）vs 紙餐盒最少（2,170），類別不平衡
  → v6 以 `copy_paste=0.3` + `cls=0.3` 緩解
- Roboflow API Key 需妥善保管（存於 Kaggle Secrets，不入 git）
- 資料集為英文標注，需依賴 NAME_MAP 正確對應，mapping 錯誤影響訓練

## 廢棄策略：原三層資料策略（TACO + TrashNet）

以下為原始設計（2026-05-30），保留供參考，實際未採用：

### 廢棄原因

| 方案 | 問題 |
|------|------|
| TrashNet v1-v2 | 分類資料集（無 bbox），轉換時全圖框（0.5,0.5,1.0,1.0），模型只學到「物件填滿畫面才偵測」，真實場景完全失效（mAP 表面 0.795，但無定位能力）|
| TACO v3 | 類別 mapping 噪音嚴重（一般垃圾標注混雜），mAP 從 0.795 暴跌至 0.439 |

### 教訓
**資料品質 > 資料量。** 確認 bbox 為真實標注是第一步，其次才考慮資料量與多樣性。

## Alternatives Considered

### Option A — 純 TrashNet
已嘗試（v1-v2），因無真實 bbox 而廢棄。

### Option B — 純 TACO
已嘗試（v3），因標注噪音嚴重（mAP=0.439）而廢棄。

### Option C — 完全自拍
8 週內無法收集足夠多樣資料（目標 5000 張以上）。
**未選原因：時間與資源不足；Roboflow 公開資料集已有足夠多樣性。**
