"""
tests/test_gpio.py — GPIOController 單元測試

強制 ENV=dev，確保所有測試使用 MockGPIO，不需要硬體。
"""

import os
import sys
import time
import threading

os.environ["ENV"] = "dev"

# 確保專案根目錄在路徑中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from gpio_controller import GPIOController
from config import GPIO_LED, WASTE_CLASSES


@pytest.fixture
def gpio():
    ctrl = GPIOController()
    yield ctrl
    ctrl.cleanup()


def test_activate_known_color(gpio):
    """點亮已知 LED 不應拋出例外。"""
    for color in GPIO_LED:
        gpio.activate(color, duration=0.1)
        assert gpio.active_color == color


def test_activate_unknown_color(gpio):
    """點亮不存在的 LED 顏色應靜默忽略，不崩潰。"""
    gpio.activate("purple", duration=0.1)
    # active_color 應保持 None（未觸發任何 LED）
    assert gpio.active_color != "purple"


def test_led_mutual_exclusion(gpio):
    """連續觸發不同 LED，同時只有最後一個為 active。"""
    gpio.activate("green", duration=5.0)
    gpio.activate("red",   duration=5.0)
    assert gpio.active_color == "red"


def test_all_off(gpio):
    """all_off() 後 active_color 應為 None。"""
    gpio.activate("blue", duration=5.0)
    gpio.all_off()
    assert gpio.active_color is None


def test_auto_off(gpio):
    """LED 應在 duration 到期後自動熄滅。"""
    gpio.activate("yellow", duration=0.2)
    assert gpio.active_color == "yellow"
    time.sleep(0.4)
    assert gpio.active_color is None


def test_all_waste_classes_have_valid_led(gpio):
    """config 中每個 waste class 的 led 顏色都必須對應到 GPIO_LED。"""
    for class_id, info in WASTE_CLASSES.items():
        assert info["led"] in GPIO_LED, (
            f"class_id={class_id} ({info['zh']}) 的 LED 顏色 "
            f"'{info['led']}' 不在 GPIO_LED 中"
        )


def test_concurrent_activate(gpio):
    """多執行緒同時觸發不應造成崩潰或死鎖。"""
    errors = []

    def trigger(color):
        try:
            gpio.activate(color, duration=0.5)
        except Exception as e:
            errors.append(e)

    threads = [
        threading.Thread(target=trigger, args=(c,))
        for c in list(GPIO_LED.keys()) * 3
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=2.0)

    assert not errors, f"並發觸發出現例外：{errors}"


def test_cleanup_idempotent(gpio):
    """重複呼叫 cleanup() 不應崩潰。"""
    gpio.cleanup()
    gpio.cleanup()
