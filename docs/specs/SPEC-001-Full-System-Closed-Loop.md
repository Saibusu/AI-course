---
Title: Full System Closed-Loop (Sense → Process → Decide → Act)
Date: 2026-05-30
ADR: ADR-001, ADR-003
---

## Goal
建立一個完整的 Sense→Process→Decide→Act 閉環系統，使用 IMX219 攝影機擷取影像，
透過 YOLOE-11s TensorRT 模型辨識垃圾類別，並點亮對應 GPIO LED 指示燈 5 秒。

## Inputs
- IMX219 CSI 攝影機影像幀（連續串流，416×416 px after resize）
- 使用者將垃圾舉至攝影機掃描區（距離 30–50 cm）
- 系統啟動時載入 `.engine` TensorRT 模型檔

## Outputs
**成功路徑：**
- 辨識出類別（信心 ≥ 0.45）→ 對應 GPIO LED 點亮 5 秒 + 蜂鳴器短鳴 1 聲
- Console log：`[HH:MM:SS] class=<類別> conf=<信心值> gpio=Pin<XX>`

**失敗路徑：**
- 信心 < 0.45 → 紅色 LED（一般垃圾）點亮 + Console log: `[FALLBACK] conf=<值>`
- 模型例外 → log error，不觸發任何 GPIO，繼續下一幀

## Side Effects
- GPIO Pin 數位輸出：HIGH 5 秒後自動 LOW（Timer thread 控制）
- 蜂鳴器 GPIO Pin 17：辨識成功時 HIGH 0.2 秒
- 每次辨識結果追加寫入 `logs/detections.csv`（timestamp, class, confidence）

## Edge Cases
| 場景 | 處理方式 |
|------|---------|
| 畫面中無物體 | 不觸發 GPIO，持續等待 |
| 多個物體同時出現 | 取信心最高者 |
| GPIO 初始化失敗（非 Jetson 環境） | 降級為 mock mode，只 log 不觸發 |
| 攝影機無法開啟 | 印出錯誤訊息後退出，exit code 1 |
| LED 已亮時再次偵測 | 重置計時器，延長 5 秒 |

## Done When
- [ ] 系統可在 Orin Nano 上以 `python src/main.py` 啟動，無例外退出
- [ ] 對著鏡頭舉起寶特瓶，綠色 LED 在 500ms 內點亮
- [ ] LED 在 5 秒後自動熄滅（誤差 ≤ 0.5 秒）
- [ ] 推論速度 ≥ 10 FPS（Console 顯示 FPS 計數）
- [ ] `logs/detections.csv` 記錄每筆辨識結果
- [ ] 在非 Jetson 環境（PC）執行時自動進入 mock mode，不 crash

## Rollback Plan
- 系統為單一 Python 程序，停止方式：`Ctrl+C` 或 `kill <PID>`
- GPIO cleanup 在 `finally` 區塊執行，中斷後 LED 自動熄滅
- 若 TensorRT engine 不相容，改用 `yoloe-11s-seg.pt`（PyTorch 模式）啟動
