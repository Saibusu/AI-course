"""
test_gpio.py — GPIO 硬體測試腳本（Week 13 接線完成後使用）
智慧零接觸垃圾分類系統

依序點亮每個 LED 並觸發蜂鳴器，確認接線正確。

使用方式：
  python test_gpio.py            # 完整循環測試
  python test_gpio.py --led red  # 只測試指定顏色
"""

import argparse
import time
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)


def test_all_leds(gpio, interval: float = 1.5) -> None:
    """依序點亮所有 LED，每個亮 interval 秒。"""
    from config import WASTE_CLASSES

    logger.info("開始完整 LED 測試…")
    for class_id, info in WASTE_CLASSES.items():
        color = info["led"]
        logger.info(f"  測試 {color.upper()} LED → {info['zh']} ({info['en']})")
        gpio.activate(color, duration=interval)
        time.sleep(interval + 0.3)  # 等待熄滅 + 間隔

    logger.info("✅ 完整 LED 測試完成")


def test_single_led(gpio, color: str, duration: float = 3.0) -> None:
    logger.info(f"測試 {color.upper()} LED（持續 {duration} 秒）…")
    gpio.activate(color, duration=duration)
    time.sleep(duration + 0.5)
    logger.info(f"✅ {color.upper()} LED 測試完成")


def test_buzzer_only() -> None:
    """單獨測試蜂鳴器。"""
    try:
        import Jetson.GPIO as GPIO
        from config import GPIO_BUZZER, BUZZER_DURATION
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(GPIO_BUZZER, GPIO.OUT, initial=GPIO.LOW)

        logger.info("測試蜂鳴器…")
        GPIO.output(GPIO_BUZZER, GPIO.HIGH)
        time.sleep(BUZZER_DURATION)
        GPIO.output(GPIO_BUZZER, GPIO.LOW)
        logger.info("✅ 蜂鳴器測試完成")
        GPIO.cleanup()
    except ImportError:
        logger.warning("非 Jetson 環境，跳過蜂鳴器測試")


def main():
    parser = argparse.ArgumentParser(description="GPIO 硬體測試")
    parser.add_argument("--led", choices=["green", "yellow", "blue", "white", "orange", "red"],
                        help="只測試指定顏色的 LED")
    parser.add_argument("--buzzer-only", action="store_true",
                        help="只測試蜂鳴器")
    parser.add_argument("--duration", type=float, default=1.5,
                        help="每個 LED 亮燈秒數")
    args = parser.parse_args()

    from gpio_controller import GPIOController
    gpio = GPIOController()

    try:
        if args.buzzer_only:
            test_buzzer_only()
        elif args.led:
            test_single_led(gpio, args.led, args.duration)
        else:
            test_all_leds(gpio, args.duration)
    finally:
        gpio.cleanup()


if __name__ == "__main__":
    main()
