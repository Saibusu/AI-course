#!/usr/bin/env python3
# Copyright (c) 2026 李軒杰, 黃義鈞
# Datung University — I4210 AI實務專題
"""Unit tests for DetectionLogger — uses temp directory, no Jetson required."""

import csv
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def logger(tmp_path, monkeypatch):
    """DetectionLogger writing to a temp file."""
    log_file = str(tmp_path / "detections.csv")
    monkeypatch.setattr("src.logger_util.LOG_FILE", log_file)
    from src.logger_util import DetectionLogger
    return DetectionLogger()


def test_header_written_on_init(logger, tmp_path):
    log_file = str(tmp_path / "detections.csv")
    assert os.path.exists(log_file)
    with open(log_file, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
    assert header == ["timestamp", "class_id", "class_name", "confidence"]


def test_log_writes_row(logger, tmp_path):
    log_file = str(tmp_path / "detections.csv")
    logger.log(0, 0.85)
    with open(log_file, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert len(rows) == 2  # header + 1 data row
    assert rows[1][1] == "0"
    assert rows[1][2] == "寶特瓶"
    assert rows[1][3] == "0.8500"


def test_log_multiple_rows(logger, tmp_path):
    log_file = str(tmp_path / "detections.csv")
    logger.log(1, 0.90)
    logger.log(4, 0.60)
    with open(log_file, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert len(rows) == 3


def test_log_unknown_class(logger, tmp_path):
    log_file = str(tmp_path / "detections.csv")
    logger.log(99, 0.50)
    with open(log_file, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert rows[1][2] == "unknown"


def test_no_duplicate_header_on_existing_file(tmp_path, monkeypatch):
    log_file = str(tmp_path / "detections.csv")
    monkeypatch.setattr("src.logger_util.LOG_FILE", log_file)
    from src.logger_util import DetectionLogger
    DetectionLogger()  # creates file + header
    DetectionLogger()  # should NOT write another header
    with open(log_file, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    header_count = sum(1 for r in rows if r == ["timestamp", "class_id", "class_name", "confidence"])
    assert header_count == 1
