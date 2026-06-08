import sys, os, time
import numpy as np

import gi
gi.require_version('Gst', '1.0')
gi.require_version('GLib', '2.0')
from gi.repository import Gst, GLib

CLASS_NAMES = ['寶特瓶', '鐵鋁罐', '紙餐盒', '塑膠袋', '鋁箔包', '一般垃圾']

# Prefer ONNX (avoids PyTorch 2.5.0a0 C++ crash on Jetson); fall back to .pt
_base = os.path.expanduser('~/AI-course/models/best')
MODEL_PT = _base + '.onnx' if os.path.exists(_base + '.onnx') else _base + '.pt'

Gst.init(None)

# Capture pipeline
cap_pipe_str = (
    "nvarguscamerasrc sensor-id=0 ! "
    "video/x-raw(memory:NVMM), width=1280, height=720, framerate=30/1 ! "
    "nvvidconv ! video/x-raw, format=BGRx ! "
    "videoconvert ! video/x-raw, format=BGR ! "
    "appsink name=sink max-buffers=1 drop=true sync=false"
)

# Display pipeline
disp_pipe_str = (
    "appsrc name=src format=time is-live=true "
    "caps=video/x-raw,format=BGR,width=1280,height=720,framerate=30/1 ! "
    "videoconvert ! autovideosink sync=false"
)

print("Loading model...")
from ultralytics import YOLO
model = YOLO(MODEL_PT)
print("Model loaded. Press Ctrl+C to quit.")

cap_pipe  = Gst.parse_launch(cap_pipe_str)
disp_pipe = Gst.parse_launch(disp_pipe_str)

sink = cap_pipe.get_by_name('sink')
src  = disp_pipe.get_by_name('src')

cap_pipe.set_state(Gst.State.PLAYING)
disp_pipe.set_state(Gst.State.PLAYING)
time.sleep(2)

frame_n = 0
last_annotated = None

try:
    while True:
        sample = sink.emit('pull-sample')
        if sample is None:
            time.sleep(0.005)
            continue

        buf  = sample.get_buffer()
        caps = sample.get_caps()
        h = caps.get_structure(0).get_value('height')
        w = caps.get_structure(0).get_value('width')

        ok, map_info = buf.map(Gst.MapFlags.READ)
        if not ok:
            continue
        frame = np.frombuffer(map_info.data, dtype=np.uint8).reshape((h, w, 3)).copy()
        buf.unmap(map_info)

        # 每 3 幀推論一次
        if frame_n % 3 == 0:
            results = model(frame, imgsz=416, conf=0.45, verbose=False)
            last_annotated = results[0].plot()

            # 印出偵測到的物體
            for r in results:
                if r.boxes and len(r.boxes):
                    for box in r.boxes:
                        cls_id = int(box.cls[0])
                        conf   = float(box.conf[0])
                        name   = CLASS_NAMES[cls_id] if cls_id < len(CLASS_NAMES) else str(cls_id)
                        print(f"\r偵測到: {name}  {conf:.1%}    ", end='', flush=True)

        # 推送到顯示 pipeline
        display_frame = last_annotated if last_annotated is not None else frame
        gst_buf = Gst.Buffer.new_wrapped(display_frame.tobytes())
        src.emit('push-buffer', gst_buf)

        frame_n += 1

except KeyboardInterrupt:
    print("\nStopping...")

cap_pipe.set_state(Gst.State.NULL)
disp_pipe.set_state(Gst.State.NULL)
print("Done.")
