import os, time
import numpy as np
import cv2

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst

CLASS_NAMES = ['寶特瓶', '鐵鋁罐', '紙餐盒', '塑膠袋', '一般垃圾']   # v4: 5-class
# ASCII labels for cv2.putText (OpenCV cannot render CJK characters)
CLASS_LABELS = ['Bottle', 'MetalCan', 'PaperBox', 'Bag', 'General']
COLORS = [
    (0, 255, 0),     # 寶特瓶   — green
    (0, 255, 255),   # 鐵鋁罐   — yellow
    (255, 0, 0),     # 紙餐盒   — blue
    (200, 200, 200), # 塑膠袋   — white
    (0, 0, 255),     # 一般垃圾 — red
]

MODEL_ONNX  = os.path.expanduser('~/AI-course/models/best_v4.onnx')
CONF_THRESH = 0.50
NMS_THRESH  = 0.45
INPUT_SIZE  = 416
W, H        = 1280, 720

# ── Load model ────────────────────────────────────────────────────────────────
print("Loading model (OpenCV DNN)...")
net = cv2.dnn.readNetFromONNX(MODEL_ONNX)
print("Model loaded. Starting pipelines...")

# ── GStreamer pipelines ───────────────────────────────────────────────────────
Gst.init(None)

cap_pipe_str = (
    "nvarguscamerasrc sensor-id=0 ! "
    f"video/x-raw(memory:NVMM), width={W}, height={H}, framerate=30/1 ! "
    "nvvidconv ! video/x-raw, format=BGRx ! "
    "videoconvert ! video/x-raw, format=BGR ! "
    "appsink name=sink max-buffers=1 drop=true sync=false"
)
disp_pipe_str = (
    "appsrc name=src format=time is-live=true "
    f"caps=video/x-raw,format=BGR,width={W},height={H},framerate=30/1 ! "
    "videoconvert ! autovideosink sync=false"
)

cap_pipe  = Gst.parse_launch(cap_pipe_str)
disp_pipe = Gst.parse_launch(disp_pipe_str)
sink = cap_pipe.get_by_name('sink')
src  = disp_pipe.get_by_name('src')

cap_pipe.set_state(Gst.State.PLAYING)
disp_pipe.set_state(Gst.State.PLAYING)
time.sleep(2)
print("Ready. Press Ctrl+C to quit.\n")


def postprocess(output, orig_w, orig_h):
    """Parse YOLO11 ONNX output (1, 10, 3549) → list of (x1,y1,x2,y2,conf,cls_id)"""
    preds = output[0].T          # (3549, 10)
    scale_x = orig_w / INPUT_SIZE
    scale_y = orig_h / INPUT_SIZE

    boxes, confidences, class_ids = [], [], []
    for row in preds:
        cx, cy, bw, bh = row[0], row[1], row[2], row[3]
        scores = row[4:]
        cls_id = int(np.argmax(scores))
        conf   = float(scores[cls_id])
        if conf < CONF_THRESH:
            continue
        x1 = int((cx - bw / 2) * scale_x)
        y1 = int((cy - bh / 2) * scale_y)
        x2 = int((cx + bw / 2) * scale_x)
        y2 = int((cy + bh / 2) * scale_y)
        boxes.append([x1, y1, x2 - x1, y2 - y1])
        confidences.append(conf)
        class_ids.append(cls_id)

    if not boxes:
        return []

    indices = cv2.dnn.NMSBoxes(boxes, confidences, CONF_THRESH, NMS_THRESH)
    if len(indices) == 0:
        return []
    indices = np.array(indices).flatten()

    results = []
    for i in indices:
        x, y, w, h = boxes[i]
        results.append((x, y, x + w, y + h, confidences[i], class_ids[i]))
    return results


# ── Main loop ─────────────────────────────────────────────────────────────────
frame_n      = 0
last_display = None
fps_t        = time.time()
fps_count    = 0

try:
    while True:
        sample = sink.emit('pull-sample')
        if sample is None:
            time.sleep(0.005)
            continue

        buf  = sample.get_buffer()
        ok, map_info = buf.map(Gst.MapFlags.READ)
        if not ok:
            continue
        frame = np.frombuffer(map_info.data, dtype=np.uint8).reshape((H, W, 3)).copy()
        buf.unmap(map_info)

        if frame_n % 3 == 0:
            blob = cv2.dnn.blobFromImage(
                frame, 1 / 255.0, (INPUT_SIZE, INPUT_SIZE), swapRB=True
            )
            net.setInput(blob)
            output = net.forward()
            dets   = postprocess(output, W, H)

            display = frame.copy()
            if dets:
                for (x1, y1, x2, y2, conf, cls_id) in dets:
                    color = COLORS[cls_id] if cls_id < len(COLORS) else (255, 255, 255)
                    cv2.rectangle(display, (x1, y1), (x2, y2), color, 2)
                    label = f"{CLASS_LABELS[cls_id]} {conf:.0%}"
                    cv2.putText(display, label, (x1, max(y1 - 8, 20)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
                    print(f"\r偵測到: {CLASS_NAMES[cls_id]}  {conf:.1%}    ", end='', flush=True)
            else:
                cv2.putText(display, "---", (20, 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (128, 128, 128), 2)
            last_display = display

        # FPS counter
        fps_count += 1
        if time.time() - fps_t >= 3.0:
            fps = fps_count / (time.time() - fps_t)
            print(f"\rFPS: {fps:.1f}    ", end='', flush=True)
            fps_count = 0
            fps_t = time.time()

        push_frame = last_display if last_display is not None else frame
        gst_buf = Gst.Buffer.new_wrapped(push_frame.tobytes())
        src.emit('push-buffer', gst_buf)

        frame_n += 1

except KeyboardInterrupt:
    print("\nStopping...")
finally:
    cap_pipe.set_state(Gst.State.NULL)
    disp_pipe.set_state(Gst.State.NULL)
    print("Done.")
