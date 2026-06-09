"""Unit tests for GPIOController — runs in mock mode on any platform."""

import time
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.gpio_controller import GPIOController


@pytest.fixture
def gpio():
    ctrl = GPIOController()
    assert ctrl.mock_mode, "Tests must run in mock mode"
    yield ctrl
    ctrl.cleanup()


def test_trigger_valid_class(gpio, capsys):
    gpio.trigger(0, duration=0.1)
    out = capsys.readouterr().out
    assert "Pin 11" in out
    assert "HIGH" in out


def test_trigger_fallback_class(gpio, capsys):
    gpio.trigger(5, duration=0.1)
    out = capsys.readouterr().out
    assert "Pin 23" in out


def test_trigger_invalid_class(gpio):
    gpio.trigger(99)  # should not raise


def test_led_auto_off(gpio, capsys):
    gpio.trigger(0, duration=0.15)
    time.sleep(0.3)
    out = capsys.readouterr().out
    assert "LOW" in out


def test_retrigger_resets_timer(gpio, capsys):
    gpio.trigger(0, duration=0.5)
    time.sleep(0.1)
    gpio.trigger(1, duration=0.1)
    out = capsys.readouterr().out
    assert "Pin 11 LOW" in out or "Pin 13" in out


def test_cleanup_all_low(gpio, capsys):
    gpio.trigger(2, duration=10.0)
    gpio.cleanup()
    out = capsys.readouterr().out
    assert "LOW" in out


def test_zero_duration_skipped(gpio, capsys):
    gpio.trigger(0, duration=0)
    out = capsys.readouterr().out
    assert "HIGH" not in out
