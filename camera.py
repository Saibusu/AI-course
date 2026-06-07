"""
camera.py — 攝影機封裝
智慧零接觸垃圾分類系統

ENV=dev    → USB 攝影機（/dev/video0，PC 通用）
ENV=jetson → IMX219 CSI-2（GStreamer pipeline）
"""

import logging
import cv2
import numpy as np
from config import IS_JETSON, CAMERA_ID, CAMERA_WIDTH, CAMERA_HEIGHT, CAMERA_FPS, CAMERA_FLIP

logger = logging.getLogger(__name__)


def _gstreamer_pipeline() -> str:
    """Jetson 專用 GStreamer pipeline（nvarguscamerasrc）。"""
    return (
        f"nvarguscamerasrc sensor-id={CAMERA_ID} ! "
        f"video/x-raw(memory:NVMM), width={CAMERA_WIDTH}, height={CAMERA_HEIGHT}, "
        f"format=NV12, framerate={CAMERA_FPS}/1 ! "
        f"nvvidconv flip-method={CAMERA_FLIP} ! "
        f"video/x-raw, width={CAMERA_WIDTH}, height={CAMERA_HEIGHT}, format=BGRx ! "
        f"videoconvert ! video/x-raw, format=BGR ! appsink"
    )


class Camera:
    """
    攝影機封裝器。
    PC(dev)   → cv2.VideoCapture(CAMERA_ID)，支援 USB 或虛擬攝影機
    Jetson    → GStreamer CSI-2，失敗則 fallback USB
    """

    def __init__(self):
        self._cap: cv2.VideoCapture | None = None
        self._open()

    def _open(self) -> None:
        if IS_JETSON:
            self._open_csi()
        else:
            self._open_usb()

    def _open_csi(self) -> None:
        pipeline = _gstreamer_pipeline()
        cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
        if cap.isOpened():
            self._cap = cap
            logger.info("✅ CSI-2 攝影機（IMX219）已開啟")
            return
        logger.warning("CSI 攝影機無法開啟，fallback → USB")
        self._open_usb()

    def _open_usb(self) -> None:
        cap = cv2.VideoCapture(CAMERA_ID)
        if not cap.isOpened():
            raise RuntimeError(
                f"無法開啟攝影機 index={CAMERA_ID}。\n"
                "  PC：確認 USB 攝影機已插入，或設定 CAMERA_ID 環境變數\n"
                "  Docker：確認 --device=/dev/video0 已掛載"
            )
        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  CAMERA_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
        cap.set(cv2.CAP_PROP_FPS,          CAMERA_FPS)
        self._cap = cap
        logger.info(f"✅ USB 攝影機已開啟（index={CAMERA_ID}）")

    def read(self) -> tuple[bool, np.ndarray | None]:
        if not self.is_opened:
            return False, None
        return self._cap.read()

    def release(self) -> None:
        if self._cap:
            self._cap.release()
            logger.info("攝影機資源已釋放")

    @property
    def is_opened(self) -> bool:
        return self._cap is not None and self._cap.isOpened()

    def __enter__(self): return self
    def __exit__(self, *_): self.release()
