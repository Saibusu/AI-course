#!/usr/bin/env python3
# Copyright (c) 2026 李軒杰, 黃義鈞
# Datung University — I4210 AI實務專題
import csv
import os
import logging
from datetime import datetime
from src.config import LOG_FILE, CLASS_NAMES

logger = logging.getLogger(__name__)


class DetectionLogger:
    def __init__(self):
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        self._write_header()

    def _write_header(self) -> None:
        if not os.path.exists(LOG_FILE):
            with open(LOG_FILE, "w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(["timestamp", "class_id", "class_name", "confidence"])

    def log(self, class_id: int, confidence: float) -> None:
        row = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            class_id,
            CLASS_NAMES[class_id] if class_id < len(CLASS_NAMES) else "unknown",
            f"{confidence:.4f}",
        ]
        try:
            with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(row)
        except OSError as e:
            logger.error("Log write error: %s", e)
