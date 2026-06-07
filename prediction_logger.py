"""
prediction_logger.py — 辨識結果 CSV 紀錄器
智慧零接觸垃圾分類系統 | Jetson Orin Nano
"""

import csv
import logging
import threading
from datetime import datetime
from pathlib import Path

from config import LOG_PATH, LOG_PREDICTIONS
from classifier import Prediction

logger = logging.getLogger(__name__)


class PredictionLogger:
    """
    將每次辨識結果寫入 CSV 檔案。
    欄位：timestamp, class_id, class_zh, confidence, is_fallback, latency_ms
    """

    HEADERS = ["timestamp", "class_id", "class_zh", "confidence", "is_fallback", "latency_ms"]

    def __init__(self):
        self._enabled = LOG_PREDICTIONS
        self._lock = threading.Lock()
        if not self._enabled:
            return

        self._path = Path(LOG_PATH)
        self._path.parent.mkdir(parents=True, exist_ok=True)

        # 若檔案不存在，寫入表頭
        write_header = not self._path.exists()
        self._file = open(self._path, "a", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(self._file, fieldnames=self.HEADERS)
        if write_header:
            self._writer.writeheader()

        logger.info(f"辨識記錄檔：{self._path.resolve()}")

    def log(self, pred: Prediction) -> None:
        """寫入一筆辨識結果（執行緒安全）。"""
        if not self._enabled:
            return
        with self._lock:
            self._writer.writerow({
                "timestamp":  datetime.now().isoformat(timespec="milliseconds"),
                "class_id":   pred.class_id,
                "class_zh":   pred.class_zh,
                "confidence": f"{pred.confidence:.4f}",
                "is_fallback": int(pred.is_fallback),
                "latency_ms": f"{pred.latency_ms:.2f}",
            })
            self._file.flush()

    def close(self) -> None:
        with self._lock:
            if self._enabled and not self._file.closed:
                self._file.close()
