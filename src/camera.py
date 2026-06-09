#!/usr/bin/env python3
# Copyright (c) 2026 李軒杰, 黃義鈞
# Datung University — I4210 AI實務專題
import logging
import numpy as np
from src.config import CAMERA_WIDTH, CAMERA_HEIGHT

logger = logging.getLogger(__name__)

_GST_PIPELINE = (
    "nvarguscamerasrc sensor-id=0 ! "
    "video/x-raw(memory:NVMM), width=(int){w}, height=(int){h}, framerate=(fraction)30/1 ! "
    "nvvidconv ! video/x-raw, format=(string)BGRx ! "
    "videoconvert ! video/x-raw, format=(string)BGR ! "
    "appsink name=sink max-buffers=1 drop=true sync=false"
)


class _GstCapture:
    """cv2.VideoCapture-compatible wrapper backed by GStreamer appsink."""

    def __init__(self, w: int, h: int):
        import gi
        gi.require_version("Gst", "1.0")
        from gi.repository import Gst
        import time

        Gst.init(None)
        pipeline_str = _GST_PIPELINE.format(w=w, h=h)
        self._pipeline = Gst.parse_launch(pipeline_str)
        self._sink = self._pipeline.get_by_name("sink")
        self._pipeline.set_state(Gst.State.PLAYING)
        self._w = w
        self._h = h
        time.sleep(1.5)  # wait for pipeline to start

    def isOpened(self) -> bool:
        return self._pipeline is not None

    def read(self):
        from gi.repository import Gst
        sample = self._sink.emit("pull-sample")
        if sample is None:
            return False, None
        buf = sample.get_buffer()
        ok, map_info = buf.map(Gst.MapFlags.READ)
        if not ok:
            return False, None
        frame = np.frombuffer(map_info.data, dtype=np.uint8).reshape(
            (self._h, self._w, 3)
        ).copy()
        buf.unmap(map_info)
        return True, frame

    def release(self):
        if self._pipeline:
            self._pipeline.set_state(
                __import__("gi").repository.Gst.State.NULL
            )
            self._pipeline = None


def open_camera() -> _GstCapture:
    # Try GStreamer via gi (works even when OpenCV has no GStreamer support)
    try:
        cap = _GstCapture(CAMERA_WIDTH, CAMERA_HEIGHT)
        logger.info("Camera opened via GStreamer gi (%dx%d)", CAMERA_WIDTH, CAMERA_HEIGHT)
        return cap
    except Exception as e:
        raise RuntimeError(
            f"Cannot open CSI camera via GStreamer: {e}\n"
            "Check that nvarguscamerasrc is installed and CSI cable is connected."
        ) from e
