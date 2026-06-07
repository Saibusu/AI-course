"""
tests/test_classifier.py — WasteClassifier 單元測試

使用 unittest.mock patch 掉 ultralytics YOLO，不需要實際模型檔案。
"""

import os
import sys
from unittest.mock import MagicMock, patch, PropertyMock

os.environ["ENV"] = "dev"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import pytest
from classifier import WasteClassifier, Prediction
from config import WASTE_CLASSES, DEFAULT_CLASS_ID, CONFIDENCE_THRESHOLD


def _make_mock_box(class_id: int, confidence: float):
    """建立模擬 ultralytics bounding box 物件。"""
    box = MagicMock()
    box.cls  = MagicMock()
    box.cls.__getitem__ = lambda self, i: class_id
    box.conf = MagicMock()
    box.conf.__getitem__ = lambda self, i: confidence
    box.conf.argmax = MagicMock(return_value=0)
    box.xyxy = MagicMock()
    box.xyxy.__getitem__ = lambda self, i: [10.0, 10.0, 100.0, 100.0]
    return box


def _make_mock_results(class_id: int, confidence: float):
    """建立包含一個 box 的模擬 ultralytics Results 列表。"""
    box = _make_mock_box(class_id, confidence)

    boxes = MagicMock()
    boxes.__len__ = MagicMock(return_value=1)
    boxes.__getitem__ = MagicMock(return_value=box)
    boxes.conf = MagicMock()
    boxes.conf.argmax = MagicMock(return_value=0)

    result = MagicMock()
    result.boxes = boxes

    return [result]


def _make_empty_results():
    """建立無偵測結果的模擬 Results 列表。"""
    result = MagicMock()
    result.boxes = None
    return [result]


@pytest.fixture
def classifier():
    """建立使用 mock YOLO 的 WasteClassifier，直接繞過 _load_model。"""
    mock_yolo = MagicMock()
    with patch.object(WasteClassifier, "_load_model"):
        clf = WasteClassifier()
    clf._model = mock_yolo
    clf._backend = "mock"
    return clf, mock_yolo


class TestPredictionFallback:
    """測試 fallback 機制。"""

    def test_no_detection_returns_fallback(self, classifier):
        clf, mock_model = classifier
        mock_model.return_value = _make_empty_results()

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        pred = clf.predict(frame)

        assert pred.is_fallback is True
        assert pred.class_id == DEFAULT_CLASS_ID
        assert pred.confidence == 0.0
        assert pred.bbox is None

    def test_unknown_class_id_returns_fallback(self, classifier):
        clf, mock_model = classifier
        mock_model.return_value = _make_mock_results(class_id=99, confidence=0.9)

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        pred = clf.predict(frame)

        assert pred.is_fallback is True
        assert pred.class_id == DEFAULT_CLASS_ID


class TestPredictionResult:
    """測試正常推論結果的欄位正確性。"""

    @pytest.mark.parametrize("class_id", list(WASTE_CLASSES.keys()))
    def test_all_classes_return_correct_fields(self, classifier, class_id):
        clf, mock_model = classifier
        mock_model.return_value = _make_mock_results(class_id=class_id, confidence=0.95)

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        pred = clf.predict(frame)

        expected = WASTE_CLASSES[class_id]
        assert pred.class_id  == class_id
        assert pred.class_zh  == expected["zh"]
        assert pred.class_en  == expected["en"]
        assert pred.led_color == expected["led"]
        assert pred.is_fallback is False
        assert pred.confidence > 0.0
        assert pred.latency_ms >= 0.0

    def test_bbox_mapped_to_original_frame(self, classifier):
        clf, mock_model = classifier
        mock_model.return_value = _make_mock_results(class_id=0, confidence=0.9)

        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        pred = clf.predict(frame)

        assert pred.bbox is not None
        x1, y1, x2, y2 = pred.bbox
        assert 0 <= x1 < x2 <= 1280
        assert 0 <= y1 < y2 <= 720


class TestPredictionDataclass:
    """測試 Prediction dataclass 的結構。"""

    def test_prediction_has_required_fields(self):
        pred = Prediction(
            class_id=0,
            class_zh="寶特瓶",
            class_en="PET Bottle",
            led_color="green",
            confidence=0.85,
            is_fallback=False,
            bbox=(10, 10, 100, 100),
            latency_ms=12.5,
        )
        assert pred.class_id == 0
        assert pred.led_color == "green"
        assert pred.latency_ms == 12.5


class TestWasteConfig:
    """測試設定的完整性。"""

    def test_all_classes_have_required_keys(self):
        for class_id, info in WASTE_CLASSES.items():
            assert "zh"  in info, f"class_id={class_id} 缺少 'zh'"
            assert "en"  in info, f"class_id={class_id} 缺少 'en'"
            assert "led" in info, f"class_id={class_id} 缺少 'led'"

    def test_default_class_id_exists(self):
        assert DEFAULT_CLASS_ID in WASTE_CLASSES

    def test_class_ids_are_contiguous(self):
        ids = sorted(WASTE_CLASSES.keys())
        assert ids == list(range(len(ids))), "class_id 應從 0 連續遞增"
