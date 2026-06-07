"""
main.py — 主程式入口
智慧零接觸垃圾分類系統 | Jetson Orin Nano
作者：李軒杰（I4A70）、黃義鈞（I4B58）

執行方式：
  python main.py              # 正常執行（含預覽視窗）
  python main.py --no-preview # 無頭模式（部署環境）
  python main.py --debug      # 詳細 log 輸出

系統流程（閉環）：
  SENSE  → IMX219 攝影機擷取影像幀
  PROCESS→ YOLO TensorRT 推論垃圾類別
  DECIDE → 類別 ID 映射 LED 顏色 + fallback 判斷
  ACT    → GPIO 觸發 LED 亮燈 + 蜂鳴器提示音
"""

import argparse
import logging
import sys
import time

import cv2

from camera import Camera
from classifier import WasteClassifier, Prediction
from gpio_controller import GPIOController
from prediction_logger import PredictionLogger
from config import (
    SHOW_PREVIEW, COOLDOWN_DURATION,
    WASTE_CLASSES, CONFIDENCE_THRESHOLD,
)

# ── 顏色常數（BGR，OpenCV 預覽用）────────────────────────────────────
_LED_BGR = {
    "green":  (0,   200,   0),
    "yellow": (0,   200, 200),
    "blue":   (200,   0,   0),
    "white":  (220, 220, 220),
    "orange": (0,   140, 255),
    "red":    (0,     0, 200),
}
_WHITE  = (255, 255, 255)
_GRAY   = (150, 150, 150)
_BLACK  = (0, 0, 0)


def _setup_logging(debug: bool) -> None:
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def _draw_overlay(frame, pred: Prediction, fps: float, in_cooldown: bool) -> None:
    """在預覽畫面上繪製辨識結果疊加層。"""
    h, w = frame.shape[:2]
    color = _LED_BGR.get(pred.led_color, _WHITE)

    # ── Bounding Box ──────────────────────────────────────────────
    if pred.bbox is not None:
        x1, y1, x2, y2 = pred.bbox
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

    # ── 主要資訊面板（左上角）────────────────────────────────────
    panel_lines = [
        f"類別：{pred.class_zh}",
        f"Class: {pred.class_en}",
        f"信心：{pred.confidence:.1%}" + (" [FALLBACK]" if pred.is_fallback else ""),
        f"延遲：{pred.latency_ms:.1f} ms | FPS：{fps:.1f}",
    ]
    for i, line in enumerate(panel_lines):
        y = 30 + i * 28
        cv2.putText(frame, line, (10, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, _BLACK, 3, cv2.LINE_AA)
        cv2.putText(frame, line, (10, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, color,  1, cv2.LINE_AA)

    # ── LED 狀態指示（右上角）──────────────────────────────────
    for i, (color_name, info) in enumerate(WASTE_CLASSES.items()):
        x = w - 180
        y = 30 + i * 32
        is_active = (info["led"] == pred.led_color and not in_cooldown)
        dot_color = _LED_BGR[info["led"]] if is_active else _GRAY
        cv2.circle(frame, (x + 8, y - 8), 8, dot_color, -1)
        label = f"{info['zh']}  [{info['led'].upper()[:1]}]"
        cv2.putText(frame, label, (x + 22, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    dot_color if is_active else _GRAY, 1, cv2.LINE_AA)

    # ── 冷卻提示 ──────────────────────────────────────────────────
    if in_cooldown:
        msg = "[ 等待中… ]"
        tw, _ = cv2.getTextSize(msg, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0], None
        cv2.putText(frame, msg, (w // 2 - 60, h - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, _WHITE, 2, cv2.LINE_AA)

    # ── 操作提示 ──────────────────────────────────────────────────
    cv2.putText(frame, "按 Q 離開", (10, h - 12),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, _GRAY, 1, cv2.LINE_AA)


def run(show_preview: bool = True) -> None:
    """主執行迴圈。"""
    gpio   = GPIOController()
    cam    = Camera()
    model  = WasteClassifier()
    logger = PredictionLogger()

    logging.info(
        f"\n{'='*50}\n"
        f"  智慧垃圾分類系統啟動\n"
        f"  模型後端：{model.backend}\n"
        f"  預覽視窗：{'開啟' if show_preview else '關閉（無頭模式）'}\n"
        f"  信心門檻：{CONFIDENCE_THRESHOLD:.0%}\n"
        f"{'='*50}"
    )

    fps_counter = 0
    fps_t0      = time.time()
    fps_display = 0.0
    last_trigger_t  = 0.0   # 上次觸發 LED 的時間（冷卻計時用）
    last_infer_t    = 0.0   # 上次推論完成的時間（跳幀基準）

    try:
        while True:
            # ── SENSE：擷取影像幀 ──────────────────────────────────
            ok, frame = cam.read()
            if not ok or frame is None:
                logging.warning("攝影機讀取失敗，重試…")
                time.sleep(0.05)
                continue

            # ── 跳幀：若上次推論太近，丟棄此幀以排空緩衝區 ──────
            # 確保每次推論拿到的都是最新幀，避免因緩衝積壓導致延遲感知
            now_pre = time.time()
            if last_infer_t and (now_pre - last_infer_t) < 0.033:
                continue

            # ── FPS 計算 ───────────────────────────────────────────
            fps_counter += 1
            elapsed = time.time() - fps_t0
            if elapsed >= 1.0:
                fps_display = fps_counter / elapsed
                fps_counter = 0
                fps_t0 = time.time()

            # ── PROCESS：YOLO 推論 ────────────────────────────────
            pred = model.predict(frame)
            last_infer_t = time.time()

            # ── DECIDE + ACT：冷卻期內不重複觸發 ──────────────────
            now = time.time()
            in_cooldown = (now - last_trigger_t) < COOLDOWN_DURATION

            if not in_cooldown and not pred.is_fallback:
                gpio.activate(pred.led_color)
                logger.log(pred)
                last_trigger_t = now
                logging.info(
                    f"▶ {pred.class_zh} ({pred.class_en}) | "
                    f"信心 {pred.confidence:.1%} | "
                    f"LED: {pred.led_color.upper()} | "
                    f"{pred.latency_ms:.1f} ms"
                )

            # ── 預覽視窗 ──────────────────────────────────────────
            if show_preview:
                _draw_overlay(frame, pred, fps_display, in_cooldown)
                cv2.imshow("智慧垃圾分類系統 | Waste Sorting", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    logging.info("使用者按下 Q，離開…")
                    break

    except KeyboardInterrupt:
        logging.info("收到中斷訊號（Ctrl+C），離開…")
    finally:
        # ── 資源清理 ──────────────────────────────────────────────
        cam.release()
        gpio.cleanup()
        logger.close()
        if show_preview:
            cv2.destroyAllWindows()
        logging.info("系統已安全關閉。")


def main() -> None:
    parser = argparse.ArgumentParser(description="智慧零接觸垃圾分類系統")
    parser.add_argument("--no-preview", action="store_true",
                        help="無頭模式，不顯示預覽視窗（部署環境使用）")
    parser.add_argument("--debug", action="store_true",
                        help="輸出詳細 debug 日誌")
    args = parser.parse_args()

    _setup_logging(args.debug)
    show = SHOW_PREVIEW and not args.no_preview
    run(show_preview=show)


if __name__ == "__main__":
    main()
