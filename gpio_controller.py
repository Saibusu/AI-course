"""
gpio_controller.py — LED 指示燈與蜂鳴器 GPIO 控制器
智慧零接觸垃圾分類系統

環境自動切換：
  ENV=dev    → MockGPIO（Console 輸出，PC 可直接執行）
  ENV=jetson → Jetson.GPIO（真實硬體）
"""

import time
import threading
import logging
from config import GPIO_LED, GPIO_BUZZER, LED_ON_DURATION, BUZZER_DURATION, IS_JETSON

logger = logging.getLogger(__name__)

# ── GPIO 後端選擇 ─────────────────────────────────────────────────────

if IS_JETSON:
    try:
        import Jetson.GPIO as GPIO
        logger.info("✅ Jetson.GPIO 已載入（硬體模式）")
    except ImportError as e:
        raise ImportError(
            "ENV=jetson 但 Jetson.GPIO 未安裝。\n"
            "請確認在 Jetson 容器內執行，或改用 ENV=dev。"
        ) from e
else:
    # ── MockGPIO：在 PC 上模擬 GPIO，讓開發/測試不需要硬體 ──
    class _MockGPIO:
        BCM = OUT = IN = HIGH = 1
        LOW  = 0

        def setmode(self, _):    pass
        def setwarnings(self, _): pass
        def cleanup(self):        pass

        def setup(self, pin, mode, initial=None):
            logger.debug(f"[MockGPIO] setup  pin={pin} initial={'HIGH' if initial else 'LOW'}")

        def output(self, pin, state):
            # 找出對應的 LED 名稱，讓 log 更易讀
            label = next(
                (f"{n.upper()} LED" for n, p in GPIO_LED.items() if p == pin),
                ("BUZZER" if pin == GPIO_BUZZER else f"Pin {pin}")
            )
            icon = "💡" if state else "⬛"
            logger.info(f"[MockGPIO] {icon}  {label:<14} {'HIGH' if state else 'LOW '}")

    GPIO = _MockGPIO()
    logger.info("⚙️  MockGPIO 已啟用（PC 開發模式）")


# ── 控制器 ────────────────────────────────────────────────────────────

class GPIOController:
    """
    LED 指示燈與蜂鳴器控制器。
    - LED 互斥：同時只有一組亮燈
    - 非阻塞：Timer 背景熄滅，不卡主迴圈
    - 執行緒安全：Lock 保護所有狀態寫入
    """

    def __init__(self):
        self._lock   = threading.Lock()
        self._timer: threading.Timer | None = None
        self._active_color: str | None = None
        self._setup()

    def _setup(self) -> None:
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        for color, pin in GPIO_LED.items():
            GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(GPIO_BUZZER, GPIO.OUT, initial=GPIO.LOW)

    # ── 公開 API ─────────────────────────────────────────────────

    def activate(self, led_color: str, duration: float = LED_ON_DURATION) -> None:
        """點亮指定 LED 並觸發蜂鳴器。"""
        if led_color not in GPIO_LED:
            logger.error(f"未知 LED 顏色：{led_color}")
            return
        with self._lock:
            self._cancel_timer()
            self._all_off()
            GPIO.output(GPIO_LED[led_color], GPIO.HIGH)
            self._active_color = led_color
            threading.Thread(target=self._beep, daemon=True).start()
            self._timer = threading.Timer(duration, self._auto_off)
            self._timer.daemon = True
            self._timer.start()

    def all_off(self) -> None:
        with self._lock:
            self._cancel_timer()
            self._all_off()

    def cleanup(self) -> None:
        self.all_off()
        GPIO.cleanup()
        logger.info("GPIO 資源已釋放")

    @property
    def active_color(self) -> str | None:
        return self._active_color

    # ── 內部方法 ─────────────────────────────────────────────────

    def _all_off(self) -> None:
        for pin in GPIO_LED.values():
            GPIO.output(pin, GPIO.LOW)
        self._active_color = None

    def _cancel_timer(self) -> None:
        if self._timer:
            self._timer.cancel()
            self._timer = None

    def _auto_off(self) -> None:
        with self._lock:
            self._all_off()

    def _beep(self) -> None:
        GPIO.output(GPIO_BUZZER, GPIO.HIGH)
        time.sleep(BUZZER_DURATION)
        GPIO.output(GPIO_BUZZER, GPIO.LOW)
