# 硬體接線說明

## 元件清單

| 元件 | 規格 | 數量 | 備註 |
|------|------|------|------|
| Jetson Orin Nano | 8GB RAM | 1 | 主控板 |
| IMX219 CSI 攝影機 | 800 萬畫素 | 1 | CSI-2 介面 |
| 高亮 LED | 2000 mcd, 5mm | 6 顆 | 綠/黃/藍/白/橙/紅各 1 |
| 限流電阻 | 220Ω | 4 顆 | 綠/黃/橙/紅 LED 用 |
| 限流電阻 | 100Ω | 2 顆 | 藍/白 LED 用（Vf≈3.0V）|
| 有源蜂鳴器 | 3.3V | 1 | GPIO 直驅 |
| 麵包板 | 830孔 | 1 | 原型接線 |
| 公對母杜邦線 | 20cm | 15 條 | GPIO 連接 |

---

## GPIO 接線對照表（Board 編號）

```
Jetson Orin Nano 40-pin Header

                    ┌──────────────────────────────┐
  3.3V Power   [1] ─┤ o o ├─ [2]  5V Power
  I2C SDA      [3] ─┤ o o ├─ [4]  5V Power
  I2C SCL      [5] ─┤ o o ├─ [6]  GND ◄── 所有 LED 的負極接這裡
  GPIO.0 ★    [7] ─┤ o o ├─ [8]  UART TX
  GND          [9] ─┤ o o ├─ [10] UART RX
  GPIO.0 ★   [11] ─┤ o o ├─ [12] GPIO.1       ★ = 本專案使用
  GPIO.2 ★   [13] ─┤ o o ├─ [14] GND
  GPIO.3 ★   [15] ─┤ o o ├─ [16] GPIO.4 ★
  3.3V Power  [17] ─┤ o o ├─ [18] GPIO.5 ★
  SPI MOSI    [19] ─┤ o o ├─ [20] GND
  GPIO.4 ★   [21] ─┤ o o ├─ [22] GPIO.6 ★... 
                    └──────────────────────────────┘
```

### 實際使用腳位

| Board Pin | 功能 | 連接元件 | 電阻 |
|-----------|------|---------|------|
| Pin 11 | 寶特瓶 LED | 綠色 LED 正極 | 220Ω |
| Pin 13 | 鐵鋁罐 LED | 黃色 LED 正極 | 220Ω |
| Pin 15 | 紙餐盒 LED | 藍色 LED 正極 | 100Ω |
| Pin 17 | 蜂鳴器 | 有源蜂鳴器 + 極 | 直連 |
| Pin 19 | 塑膠袋 LED | 白色 LED 正極 | 100Ω |
| Pin 21 | 鋁箔包 LED | 橙色 LED 正極 | 220Ω |
| Pin 23 | 一般垃圾 LED | 紅色 LED 正極 | 220Ω |
| Pin 6 / 9 / 14 / 20 | GND | 所有 LED 負極、蜂鳴器負極 | — |

---

## 接線步驟

### Step 1：GND 共地
將麵包板負極排（藍色）連接至 Jetson Pin 6（GND）。

### Step 2：每顆 LED 的接法

```
Jetson GPIO Pin → 電阻（220Ω 或 100Ω）→ LED 正極（長腳）→ LED 負極（短腳）→ GND
```

**範例：寶特瓶（綠色 LED）**
```
Pin 11 ──── 220Ω ──── 綠LED(+) ──── 綠LED(-) ──── GND
```

**範例：紙餐盒（藍色 LED，100Ω）**
```
Pin 15 ──── 100Ω ──── 藍LED(+) ──── 藍LED(-) ──── GND
```

### Step 3：蜂鳴器
```
Pin 17 ──── 有源蜂鳴器(+) ──── 有源蜂鳴器(-) ──── GND
```
注意：使用**有源**蜂鳴器（內建振盪電路），直接給 HIGH/LOW 即可發聲。

### Step 4：攝影機
IMX219 CSI 排線插入 Jetson Orin Nano 的 CAM0 CSI 接口（15-pin FPC 連接器）。
排線金屬接點朝向接口內側金屬片。

---

## 電路驗證指令

接線完成後，在 Jetson 上執行以下指令逐一測試 LED：

```bash
# 安裝 Jetson.GPIO（若尚未安裝）
pip install Jetson.GPIO

# 測試 Pin 11（綠色LED）
python3 -c "
import Jetson.GPIO as GPIO
import time
GPIO.setmode(GPIO.BOARD)
GPIO.setup(11, GPIO.OUT)
GPIO.output(11, GPIO.HIGH)
print('Pin 11 HIGH - 綠色 LED 應亮')
time.sleep(2)
GPIO.output(11, GPIO.LOW)
GPIO.cleanup()
print('Done')
"
```

將 `11` 替換為其他腳位（13, 15, 17, 19, 21, 23）依序測試。

---

## 常見問題

| 問題 | 原因 | 解決 |
|------|------|------|
| LED 不亮 | 正負極接反 | LED 長腳接正極（GPIO 端） |
| LED 非常暗 | 電阻過大（藍/白用 220Ω） | 改用 100Ω |
| LED 太亮/過熱 | 電阻過小 | 換 330Ω |
| 蜂鳴器不響 | 使用了無源蜂鳴器 | 換有源蜂鳴器 |
| GPIO permission denied | 需要 sudo 或群組 | `sudo usermod -aG gpio $USER` 後重新登入 |
