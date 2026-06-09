---
Title: GPIO LED Controller Module
Date: 2026-05-30
Updated: 2026-06-09
ADR: ADR-003
---

## Goal
建立一個線程安全的 GPIO 控制器模組，根據垃圾類別點亮對應 LED 5 秒後自動熄滅，
並在非 Jetson 環境自動降級為 mock mode。

## Inputs
- `class_id: int`（0–4，對應 5 類垃圾：寶特瓶/鐵鋁罐/紙餐盒/塑膠袋/一般垃圾）
- `duration: float`（預設 5.0 秒，由 `config.LED_DURATION` 控制）

## Outputs
**成功（Jetson）：** 對應 GPIO pin 輸出 HIGH，Timer 到期後 LOW
**成功（mock）：** Console 印出 `[MOCK GPIO] Pin XX HIGH`
**失敗：** log error，不 raise exception

## Side Effects
- GPIO 狀態變更（外部硬體）
- 建立 `threading.Timer` 物件（每次觸發一個）
- 模組初始化時設定所有 pin 為 OUTPUT + LOW

## Edge Cases
| 場景 | 處理方式 |
|------|---------|
| LED 亮燈中再次觸發同 pin | 取消舊 Timer，重新計時 5 秒 |
| LED 亮燈中觸發不同 pin | 立即熄滅舊 pin，點亮新 pin |
| GPIO 模組 import 失敗 | 設 `mock_mode=True`，繼續執行 |
| duration <= 0 | 不觸發，log warning |
| 未知 class_id（>4） | log error，不觸發任何 GPIO |

## Done When
- [ ] `GPIOController().trigger(0)` 在 Jetson 上點亮 Pin 11（綠色）5 秒後熄滅
- [ ] 在 PC/CI 上執行時自動進入 mock mode，Console 顯示 `[MOCK GPIO]` 訊息
- [ ] 快速連續觸發 10 次，不發生 threading 死鎖或 GPIO 殘留亮燈
- [ ] `cleanup()` 呼叫後所有 pin 歸 LOW
- [x] 單元測試 `tests/test_gpio.py` 全部通過（7 個測試，mock mode 下）

## Rollback Plan
- GPIO 模組為獨立 class，可在不影響主程式的情況下替換
- 若 Jetson.GPIO API 變動，mock mode 保持可用
