#!/usr/bin/env python3
# Copyright (c) 2026 李軒杰, 黃義鈞
# Datung University — I4210 AI實務專題
"""
Smart Touchless Waste Sorter — Main Entry Point
Usage: python src/main.py [--export-trt]
"""

import sys
import time
import logging
import argparse
import cv2
import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--export-trt", action="store_true", help="Export TensorRT engine then exit")
    p.add_argument("--no-display", action="store_true", help="Disable OpenCV window (headless)")
    return p.parse_args()


def main():
    args = parse_args()

    from src.detector import WasteDetector
    from src.gpio_controller import GPIOController
    from src.camera import open_camera
    from src.logger_util import DetectionLogger
    from src.config import CLASS_NAMES, CONF_THRESH, INPUT_SIZE

    detector = WasteDetector()

    if args.export_trt:
        path = detector.export_tensorrt()
        print(f"Engine saved to: {path}")
        return

    gpio = GPIOController()
    det_logger = DetectionLogger()
    cap = open_camera()

    fps_counter = 0
    fps_start = time.time()
    last_class_id = -1

    logger.info("System ready. Press Ctrl+C to stop.")
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                logger.error("Frame read failed")
                break

            resized = cv2.resize(frame, (INPUT_SIZE, INPUT_SIZE))
            class_id, conf = detector.predict(resized)

            if conf < CONF_THRESH:
                label = f"[FALLBACK] conf={conf:.2f}"
                class_id = 5
            else:
                label = f"{CLASS_NAMES[class_id]}  {conf:.2f}"

            if class_id != last_class_id or conf >= CONF_THRESH:
                gpio.trigger(class_id)
                det_logger.log(class_id, conf)
                last_class_id = class_id

            fps_counter += 1
            if time.time() - fps_start >= 1.0:
                fps = fps_counter / (time.time() - fps_start)
                logger.info("FPS: %.1f  |  %s", fps, label)
                fps_counter = 0
                fps_start = time.time()

            if not args.no_display:
                cv2.putText(frame, label, (10, 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 2)
                cv2.imshow("Waste Sorter", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        cap.release()
        gpio.cleanup()
        if not args.no_display:
            cv2.destroyAllWindows()
        logger.info("Bye.")


if __name__ == "__main__":
    main()
