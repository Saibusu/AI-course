import cv2
import logging
from src.config import CAMERA_WIDTH, CAMERA_HEIGHT

logger = logging.getLogger(__name__)

_GST_PIPELINE = (
    "nvarguscamerasrc sensor-id=0 ! "
    "video/x-raw(memory:NVMM), width=(int){w}, height=(int){h}, framerate=(fraction)30/1 ! "
    "nvvidconv ! video/x-raw, format=(string)BGRx ! "
    "videoconvert ! video/x-raw, format=(string)BGR ! appsink drop=1"
)


def open_camera() -> cv2.VideoCapture:
    gst = _GST_PIPELINE.format(w=CAMERA_WIDTH, h=CAMERA_HEIGHT)
    cap = cv2.VideoCapture(gst, cv2.CAP_GSTREAMER)

    if not cap.isOpened():
        logger.warning("GStreamer pipeline failed, falling back to /dev/video0")
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)

    if not cap.isOpened():
        raise RuntimeError("Cannot open camera. Check CSI connection or /dev/video0.")

    logger.info("Camera opened (%dx%d)", CAMERA_WIDTH, CAMERA_HEIGHT)
    return cap
