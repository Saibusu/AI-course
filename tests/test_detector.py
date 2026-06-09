"""Unit tests for WasteDetector — uses synthetic mock, no real model required."""

import pytest
import numpy as np
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _make_boxes(confs, classes):
    import torch

    class FakeBoxes:
        def __init__(self, c, cl):
            self.conf = torch.tensor(c, dtype=torch.float32)
            self.cls  = torch.tensor(cl, dtype=torch.float32)

        def __len__(self):
            return len(self.conf)

    return FakeBoxes(confs, classes)


def _make_result(confs, classes):
    class FakeResult:
        pass
    r = FakeResult()
    r.boxes = _make_boxes(confs, classes)
    return r


def _make_detector_with_model(fake_results):
    from src import detector as det_module
    d = object.__new__(det_module.WasteDetector)

    class FakeModel:
        def __call__(self, *a, **kw):
            return fake_results

    d.model = FakeModel()
    return d


def test_predict_returns_valid_class_and_conf():
    d = _make_detector_with_model([_make_result([0.85], [0.0])])
    frame = np.zeros((416, 416, 3), dtype=np.uint8)
    class_id, conf = d.predict(frame)
    assert 0 <= class_id <= 5
    assert 0.0 <= conf <= 1.0


def test_predict_fallback_on_low_confidence():
    d = _make_detector_with_model([_make_result([0.20], [1.0])])
    frame = np.zeros((416, 416, 3), dtype=np.uint8)
    class_id, conf = d.predict(frame)
    assert class_id == 5, "Low-confidence should fallback to class 5 (一般垃圾)"


def test_predict_empty_boxes():
    d = _make_detector_with_model([_make_result([], [])])
    frame = np.zeros((416, 416, 3), dtype=np.uint8)
    class_id, conf = d.predict(frame)
    assert class_id == 5
    assert conf == 0.0


def test_predict_picks_highest_confidence():
    d = _make_detector_with_model([_make_result([0.60, 0.90], [2.0, 1.0])])
    frame = np.zeros((416, 416, 3), dtype=np.uint8)
    class_id, conf = d.predict(frame)
    assert class_id == 1
    assert abs(conf - 0.90) < 1e-4
