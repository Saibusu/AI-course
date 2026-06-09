#!/usr/bin/env python3
# Copyright (c) 2026 李軒杰, 黃義鈞
# Datung University — I4210 AI實務專題
import threading
import time
import logging
from src.config import GPIO_PINS, BUZZER_PIN, LED_COLORS, LED_DURATION, BUZZER_DURATION

logger = logging.getLogger(__name__)

try:
    import Jetson.GPIO as GPIO
    _GPIO_AVAILABLE = True
except Exception:
    _GPIO_AVAILABLE = False
    logger.warning("Jetson.GPIO unavailable — running in mock mode")


class GPIOController:
    def __init__(self):
        self.mock_mode = not _GPIO_AVAILABLE
        self._active_pin: int | None = None
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()

        if not self.mock_mode:
            try:
                GPIO.setmode(GPIO.BOARD)
                for pin in GPIO_PINS.values():
                    GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)
                GPIO.setup(BUZZER_PIN, GPIO.OUT, initial=GPIO.LOW)
                logger.info("GPIO initialized (Board mode)")
            except Exception as e:
                logger.warning("GPIO setup failed (%s) — falling back to mock mode", e)
                self.mock_mode = True
        if self.mock_mode:
            logger.info("GPIO mock mode active")

    def trigger(self, class_id: int, duration: float = LED_DURATION) -> None:
        if duration <= 0:
            logger.warning("Invalid duration %s, skipping", duration)
            return

        pin = GPIO_PINS.get(class_id)
        if pin is None:
            logger.error("Unknown class_id %s", class_id)
            return

        color = LED_COLORS.get(class_id, "?")

        with self._lock:
            self._cancel_active()
            self._active_pin = pin
            self._set_pin(pin, True)
            self._beep()
            self._timer = threading.Timer(duration, self._auto_off, args=[pin])
            self._timer.daemon = True
            self._timer.start()

        logger.info("LED %s (Pin %d) ON for %.1fs", color, pin, duration)

    def _auto_off(self, pin: int) -> None:
        with self._lock:
            self._set_pin(pin, False)
            if self._active_pin == pin:
                self._active_pin = None

    def _cancel_active(self) -> None:
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None
        if self._active_pin is not None:
            self._set_pin(self._active_pin, False)
            self._active_pin = None

    def _set_pin(self, pin: int, state: bool) -> None:
        if self.mock_mode:
            print(f"[MOCK GPIO] Pin {pin} {'HIGH' if state else 'LOW'}")
            return
        try:
            GPIO.output(pin, GPIO.HIGH if state else GPIO.LOW)
        except Exception as e:
            logger.error("GPIO output error pin %d: %s", pin, e)

    def _beep(self) -> None:
        if BUZZER_PIN is None:
            return
        if self.mock_mode:
            print(f"[MOCK GPIO] Buzzer Pin {BUZZER_PIN} HIGH for {BUZZER_DURATION}s")
            return
        try:
            GPIO.output(BUZZER_PIN, GPIO.HIGH)
            threading.Timer(BUZZER_DURATION, lambda: GPIO.output(BUZZER_PIN, GPIO.LOW)).start()
        except Exception as e:
            logger.error("Buzzer error: %s", e)

    def cleanup(self) -> None:
        with self._lock:
            self._cancel_active()
        if not self.mock_mode:
            try:
                GPIO.cleanup()
            except Exception as e:
                logger.error("GPIO cleanup error: %s", e)
        logger.info("GPIO cleaned up")
