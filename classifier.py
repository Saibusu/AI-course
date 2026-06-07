"""
classifier.py — YOLO 垃圾分類推論器
智慧零接觸垃圾分類系統 | Jetson Orin Nano

支援兩種後端：
  1. TensorRT Engine（.engine）- 正式部署，最高效能
  2. PyTorch / ONNX（.pt）      - 開發測試 fallback
"""

import logging
import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from config import (
    MODEL_PATH, INPUT_SIZE,
    CONFIDENCE_THRESHOLD, NMS_IOU_THRESHOLD,
    WASTE_CLASSES, DEFAULT_CLASS_ID,
)

logger = logging.getLogger(__name__)


@dataclass
class Prediction:
    """單次推論結果。"""
    class_id:    int
    class_zh:    str
    class_en:    str
    led_color:   str
    confidence:  float
    is_fallback: bool   # True 表示信心不足，使用 fallback（一般垃圾）
    bbox:        tuple  # (x1, y1, x2, y2) 原始影像座標，無偵測時為 None
    latency_ms:  float  # 推論耗時（毫秒）


class WasteClassifier:
    """
    垃圾分類推論器。

    優先載入 TensorRT engine；若不存在則回退至 ultralytics PyTorch 模型。
    推論結果封裝為 Prediction dataclass，解耦下游邏輯。
    """

    def __init__(self):
        self._model = None
        self._backend: str = ""
        self._load_model()

    # ── 模型載入 ────────────────────────────────────────────────────

    def _load_model(self) -> None:
        engine_path = Path(MODEL_PATH)

        if engine_path.exists():
            self._load_tensorrt(engine_path)
        else:
            logger.warning(
                f"TensorRT engine 不存在：{engine_path}\n"
                "  → 嘗試載入 PyTorch 模型作為 fallback…"
            )
            self._load_pytorch_fallback()

    def _load_tensorrt(self, path: Path) -> None:
        """載入 TensorRT engine（ultralytics 統一 API）。"""
        try:
            from ultralytics import YOLO
            self._model = YOLO(str(path))
            self._backend = "tensorrt"
            logger.info(f"✅ TensorRT engine 已載入：{path}")
        except Exception as e:
            logger.error(f"TensorRT 載入失敗：{e}")
            self._load_pytorch_fallback()

    def _load_pytorch_fallback(self) -> None:
        """載入 .pt 模型作為開發/測試 fallback。"""
        from config import IS_JETSON
        pt_candidates = sorted(
            Path("models").glob("*.pt"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        if pt_candidates:
            model_path = str(pt_candidates[0])
        elif not IS_JETSON:
            # 開發模式：自動使用 yolov8n.pt（ultralytics 自動下載至快取）
            logger.warning(
                "models/ 目錄下無 .pt 模型。\n"
                "  → 使用 yolo26n.pt（YOLO26 官方通用模型，非廢棄物分類專用）\n"
                "  → 請先下載資料集：python scripts/download_dataset.py --key YOUR_KEY\n"
                "  → 再訓練分類模型：python train.py"
            )
            model_path = "yolo26n.pt"
        else:
            raise FileNotFoundError(
                "找不到任何可用模型。\n"
                "  請確認 models/ 目錄下有 .engine 或 .pt 檔案。\n"
                "  執行 export_tensorrt.py 將訓練好的 .pt 轉換為 TensorRT engine。"
            )

        try:
            from ultralytics import YOLO
            self._model = YOLO(model_path)
            self._backend = "pytorch"
            logger.info(f"✅ PyTorch 模型已載入：{model_path}")
        except Exception as e:
            raise RuntimeError(f"模型載入失敗：{e}") from e

    # ── 推論 ────────────────────────────────────────────────────────

    def predict(self, frame: np.ndarray) -> Prediction:
        """
        對單幀影像執行垃圾分類推論。

        Args:
            frame: BGR 格式 NumPy 陣列（cv2.VideoCapture 輸出）

        Returns:
            Prediction dataclass，包含分類結果、信心分數與推論延遲
        """
        resized = cv2.resize(frame, INPUT_SIZE)

        t0 = time.perf_counter()
        results = self._model(
            resized,
            conf=CONFIDENCE_THRESHOLD,
            iou=NMS_IOU_THRESHOLD,
            verbose=False,
        )
        latency_ms = (time.perf_counter() - t0) * 1000

        return self._parse_results(results, frame.shape, latency_ms)

    # ── 結果解析 ────────────────────────────────────────────────────

    def _parse_results(self, results, original_shape, latency_ms: float) -> Prediction:
        """
        從 ultralytics Results 物件萃取最高信心的預測結果。

        - 若有偵測到物件 → 取信心最高的 box
        - 若無偵測或信心不足 → 回傳 fallback（一般垃圾）
        """
        best_box = self._extract_best_box(results)

        if best_box is None:
            return self._make_fallback_prediction(latency_ms, reason="no_detection")

        class_id = int(best_box.cls[0])
        confidence = float(best_box.conf[0])

        if class_id not in WASTE_CLASSES:
            logger.warning(f"未知類別 ID：{class_id}，使用 fallback")
            return self._make_fallback_prediction(latency_ms, reason="unknown_class")

        # 將 bbox 座標映射回原始影像尺寸
        h_orig, w_orig = original_shape[:2]
        h_in, w_in = INPUT_SIZE
        x1, y1, x2, y2 = map(float, best_box.xyxy[0])
        bbox = (
            int(x1 * w_orig / w_in),
            int(y1 * h_orig / h_in),
            int(x2 * w_orig / w_in),
            int(y2 * h_orig / h_in),
        )

        info = WASTE_CLASSES[class_id]
        logger.debug(
            f"辨識結果：{info['zh']} ({confidence:.2%}) | "
            f"延遲：{latency_ms:.1f} ms | bbox：{bbox}"
        )

        return Prediction(
            class_id=class_id,
            class_zh=info["zh"],
            class_en=info["en"],
            led_color=info["led"],
            confidence=confidence,
            is_fallback=False,
            bbox=bbox,
            latency_ms=latency_ms,
        )

    @staticmethod
    def _extract_best_box(results):
        """從 Results 取信心最高的 bounding box；無偵測時回傳 None。"""
        for result in results:
            boxes = result.boxes
            if boxes is not None and len(boxes) > 0:
                best_idx = int(boxes.conf.argmax())
                return boxes[best_idx]
        return None

    @staticmethod
    def _make_fallback_prediction(latency_ms: float, reason: str) -> Prediction:
        """建立 fallback 預測（一般垃圾）。"""
        info = WASTE_CLASSES[DEFAULT_CLASS_ID]
        logger.debug(f"Fallback 觸發（{reason}）→ {info['zh']}")
        return Prediction(
            class_id=DEFAULT_CLASS_ID,
            class_zh=info["zh"],
            class_en=info["en"],
            led_color=info["led"],
            confidence=0.0,
            is_fallback=True,
            bbox=None,
            latency_ms=latency_ms,
        )

    @property
    def backend(self) -> str:
        return self._backend
