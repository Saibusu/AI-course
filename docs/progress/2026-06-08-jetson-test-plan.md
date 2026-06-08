# Jetson 推論測試計畫 — 2026-06-08

## 可用模型

| 檔案 | 模型 | 資料集 | mAP@50 | 類別數 |
|------|------|--------|--------|--------|
| `best.pt` | yolo11s | TrashNet only | 0.795 | 6 |
| `best_v2.pt` | yolo11m | TrashNet + TACO(6) | 0.794 | 6 |
| `best_v3.pt` | yolo26s | merged_v3 (TrashNet+TACO) | 0.439 | 6 |

> best.pt 和 best_v2.pt 都在本機**專案根目錄**（不在 models/，被 .gitignore 封鎖）。

---

## 修正記錄

**detector.py 修正（2026-06-08）**：
移除 `task="segment"` 硬寫，改為 ultralytics 自動偵測。
原因：best.pt / best_v2.pt 為 detection 模型，指定 task='segment' 會 crash。

---

## Jetson 操作步驟

### 環境資訊
```
Jetson IP:   172.20.10.2
User:        jetson
專案路徑:    ~/AI-course/
模型路徑:    ~/AI-course/models/best.pt  ← config.py 讀取位置
```

### Step 1：Jetson 更新程式碼

```bash
ssh jetson@172.20.10.2
cd ~/AI-course
git checkout main
git pull
```

### Step 2：從筆電 SCP 模型（在筆電終端機執行）

```bash
# 先測 best.pt（yolo11s，mAP=0.795）
scp best.pt jetson@172.20.10.2:~/AI-course/models/best.pt
```

### Step 3：Jetson 執行推論

```bash
# SSH 進 Jetson，從專案根目錄執行
cd ~/AI-course
python src/main.py --no-display
```

### Step 4：觀察輸出

正常輸出範例：
```
HH:MM:SS [INFO] main: FPS: 5.2  |  鐵鋁罐  0.87
HH:MM:SS [INFO] main: FPS: 4.8  |  [FALLBACK] conf=0.08
```

按 `Ctrl+C` 停止，結果自動寫入 `logs/detections.csv`。

---

## 觀察重點

| 項目 | 目標 | 說明 |
|------|------|------|
| FPS（PyTorch） | 3–8 FPS | TRT 轉換前，正常範圍 |
| FPS（TRT FP16）| ≥ 15 FPS | 執行 `--export-trt` 後 |
| 類別辨識 | 能識別寶特瓶、鐵鋁罐等 | 對著鏡頭拿垃圾測試 |
| FALLBACK | 無垃圾時輸出 FALLBACK | conf < 0.45 觸發 |

---

## 後續步驟

1. 確認 PyTorch 推論正常後，執行 TRT 轉換：
   ```bash
   python src/main.py --export-trt
   ```
2. TRT 轉換完成後重新執行：
   ```bash
   python src/main.py --no-display
   ```
3. 確認 FPS ≥ 15 後進行 GPIO 接線（ADR-003）
