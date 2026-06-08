import os
import logging
import numpy as np
from src.config import MODEL_ENGINE, MODEL_PT, MODEL_PRETRAIN, INPUT_SIZE, CONF_THRESH, CLASS_NAMES

logger = logging.getLogger(__name__)


class WasteDetector:
    def __init__(self):
        self.model = None
        self._load_model()

    def _load_model(self) -> None:
        from ultralytics import YOLO

        if os.path.exists(MODEL_ENGINE):
            logger.info("Loading TensorRT engine: %s", MODEL_ENGINE)
            self.model = YOLO(MODEL_ENGINE)
        elif os.path.exists(MODEL_PT):
            logger.warning("TensorRT engine not found, falling back to PyTorch: %s", MODEL_PT)
            self.model = YOLO(MODEL_PT)
        else:
            raise FileNotFoundError(
                f"No model found. Expected:\n  {MODEL_ENGINE}\n  {MODEL_PT}\n"
                f"Base model for training: {MODEL_PRETRAIN}\n"
                "Run: python data/train.py  (see SPEC-002)"
            )

    def predict(self, frame: np.ndarray) -> tuple[int, float]:
        """
        Returns (class_id, confidence).
        Returns (5, 0.0) as fallback (一般垃圾) when confidence < CONF_THRESH.
        """
        results = self.model(
            frame,
            imgsz=INPUT_SIZE,
            conf=CONF_THRESH,
            verbose=False,
        )

        best_class_id = 5    # fallback: 一般垃圾
        best_conf = 0.0

        for result in results:
            if result.boxes is None or len(result.boxes) == 0:
                continue
            confs = result.boxes.conf.cpu().numpy()
            classes = result.boxes.cls.cpu().numpy().astype(int)
            idx = int(np.argmax(confs))
            if confs[idx] >= CONF_THRESH:
                best_class_id = classes[idx]
                best_conf = float(confs[idx])
                break

        return best_class_id, best_conf

    def export_tensorrt(self) -> str:
        """Export best.pt → TensorRT FP16 engine. Run once on Jetson."""
        from ultralytics import YOLO as _YOLO
        if not os.path.exists(MODEL_PT):
            raise FileNotFoundError(f"Source model not found: {MODEL_PT}")
        model = _YOLO(MODEL_PT)
        engine_path = model.export(
            format="engine",
            imgsz=INPUT_SIZE,
            half=True,       # FP16
            device=0,
        )
        logger.info("TensorRT engine exported: %s", engine_path)
        return engine_path
