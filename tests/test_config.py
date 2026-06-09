#!/usr/bin/env python3
# Copyright (c) 2026 李軒杰, 黃義鈞
# Datung University — I4210 AI實務專題
"""Unit tests for config constants — validates 5-class system invariants."""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src import config


def test_five_classes():
    assert len(config.CLASS_NAMES) == 5, "System must have exactly 5 classes"


def test_class_names_correct():
    expected = ["寶特瓶", "鐵鋁罐", "紙餐盒", "塑膠袋", "一般垃圾"]
    assert config.CLASS_NAMES == expected


def test_gpio_pins_cover_all_classes():
    assert set(config.GPIO_PINS.keys()) == {0, 1, 2, 3, 4}


def test_gpio_pins_values_unique():
    pins = list(config.GPIO_PINS.values())
    assert len(pins) == len(set(pins)), "GPIO pins must be unique"


def test_gpio_pin_19_not_used():
    assert 19 not in config.GPIO_PINS.values(), "Pin 19 must be disabled (塑膠袋 moved to Pin 21)"


def test_led_colors_cover_all_classes():
    assert set(config.LED_COLORS.keys()) == {0, 1, 2, 3, 4}


def test_conf_thresh_is_055():
    assert config.CONF_THRESH == 0.55, f"CONF_THRESH must be 0.55, got {config.CONF_THRESH}"


def test_input_size_416():
    assert config.INPUT_SIZE == 416


def test_led_duration_positive():
    assert config.LED_DURATION > 0


def test_log_file_path_set():
    assert config.LOG_FILE and "detections.csv" in config.LOG_FILE
