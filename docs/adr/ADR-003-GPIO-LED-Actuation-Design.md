---
Title: GPIO LED Actuation Design for Waste Bin Guidance
Date: 2026-05-30
Updated: 2026-06-09
Status: Accepted
Accepted-by: Human (2026-05-30)
---

## Context

系統需要在辨識垃圾類別後，點亮對應垃圾桶上方的 LED 指示燈（5 秒後自動熄滅），
引導使用者投入正確的桶子，全程無需碰觸任何機械裝置。

Jetson Orin Nano 原生支援 GPIO 數位輸出，無需 Arduino 橋接。
GPIO 腳位額定電流：40mA MAX per pin。

## Decision

**使用 Jetson Orin Nano 原生 GPIO + 限流電阻（220Ω）直接驅動高亮 LED。**

### 類別 → GPIO → LED 顏色 對應表（5-class v5，2026-06-08 更新）

| 類別 ID | 類別 | GPIO 腳位（Board編號） | LED 顏色 | 限流電阻 |
|--------|------|----------------------|---------|---------|
| 0 | 寶特瓶 | Pin 11（GPIO.0） | 綠色 | 220Ω |
| 1 | 鐵鋁罐 | Pin 13（GPIO.2） | 黃色 | 220Ω |
| 2 | 紙餐盒 | Pin 15（GPIO.3） | 藍色 | 100Ω |
| 3 | 塑膠袋 | Pin 21（GPIO.5） | 白色 | 100Ω |
| 4 | 一般垃圾 | Pin 23（GPIO.6） | 紅色 | 220Ω |
| — | ~~鋁箔包~~ | ~~Pin 21~~ | ~~橙色~~ | 移除（資料集不足） |
| — | （停用） | Pin 19 | — | 原塑膠袋位置，已停用 |

> **變更說明（2026-06-08）**：鋁箔包因 Roboflow 資料集樣本數不足，移除為獨立類別，
> 改歸一般垃圾。塑膠袋 LED 從 Pin 19 移至 Pin 21，Pin 19 停用。系統由 6-class 縮減為 5-class。

### 電流計算
- LED 正向電壓（Vf）≈ 2.0V（紅/黃/綠）/ 3.0V（藍/白）
- GPIO 輸出電壓：3.3V
- 電流 = (3.3 - 2.0) / 220 ≈ 5.9mA（紅/黃/綠）
- 電流 = (3.3 - 3.0) / 100 ≈ 3.0mA（藍/白，100Ω）
- 全亮 5 顆：約 24mA，遠低於 40mA/pin 限制 ✅

### 藍/白 LED 電阻修正
藍色（紙餐盒 Pin 15）與白色（塑膠袋 Pin 21）LED Vf ≈ 3.0–3.2V，220Ω 電流過低。
**修正：藍色與白色 LED 使用 100Ω 限流電阻。**

### Fallback 行為
- 辨識信心 < 0.55 → 點亮紅色（一般垃圾 class 4）Pin 23
- 所有 GPIO 操作皆有 try/except，例外時僅 log，不中斷主程式

## Consequences

**正面：**
- 無需 Arduino/Pi 橋接，架構簡潔，失敗點少
- 原生 GPIO API（Jetson.GPIO）與 RPi.GPIO 相容，文件豐富
- 反應速度 < 1ms，比機械致動器快

**負面 / 風險：**
- Orin Nano GPIO 輸出 3.3V（非 5V），藍/白 LED 需注意電阻選擇
- GPIO 庫需在 Jetson 上以 sudo 或特定 group 權限執行
- 原型使用麵包板，長期可靠性需在 Week 13 壓力測試

**後續工作：**
- SPEC-003：GPIO 控制器軟體規格
- hardware/wiring.md：詳細接線圖與材料清單

## Alternatives Considered

### Option A — Arduino Uno 做 GPIO 橋接
透過 USB Serial 發送指令至 Arduino 控制 LED。
**未選原因：增加一個失敗點（USB Serial），且 Orin Nano 原生支援 GPIO，橋接是不必要的複雜性。**

### Option B — I2C PWM 擴充板（PCA9685）
可控制 16 路 PWM，支援亮度調節。
**未選原因：本專案只需數位 ON/OFF，PWM 是 over-engineering；且 I2C 設定增加 Week 11 的風險。**
