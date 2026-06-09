#!/usr/bin/env python3
import os, time
import numpy as np
import torch
import cv2

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst

CLASS_NAMES = ['寶特瓶', '鐵鋁罐', '紙餐盒', '塑膠袋', '鋁箔包', '一般垃圾']
MODEL_PT = os.path.expanduser('~/AI-course/models/best.pt')
IMGSZ = 640
CONF  = 0.45
IOU   = 0.45
W, H  = 1280, 720

Gst.init(None)

print("Loading model...")
ckpt  = torch.load(MODEL_PT, map_location='cuda', weights_only=False)
model = ckpt['model'].float().eval().cuda()
print("Model loaded. Press Ctrl+C to quit.")

def preprocess(frame):
    img = cv2.resize(frame, (IMGSZ, IMGSZ))
    img = img[:, :, ::-1].transpose(2, 0, 1)
    img = np.ascontiguousarray(img, dtype=np.float32) / 255.0
    return torch.from_numpy(img).unsqueeze(0).cuda()

def postprocess(pred, orig_h, orig_w):
    from ultralytics.utils.ops import non_max_suppression
    dets = non_max_suppression(pred, conf_thres=CONF, iou_thres=IOU)[0]
    if dets is None or len(dets) == 0:
        return []
    sx, sy = orig_w / IMGSZ, orig_h / IMGSZ
    results = []
    for d in dets.cpu().numpy():
        x1, y1, x2, y2, conf, cls = d[:6]
        results.append((int(x1*sx), int(y1*sy), int(x2*sx), int(y2*sy), float(conf), int(cls)))
    return results

def draw(frame, dets):
    for x1, y1, x2, y2, conf, cls in dets:
        name = CLASS_NAMES[cls] if cls < len(CLASS_NAMES) else str(cls)
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(frame, f'{name} {conf:.2f}', (x1, max(y1-6, 0)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2)
    return frame

cap_pipe = Gst.parse_launch(
    f"nvarguscamerasrc sensor-id=0 ! "
    f"video/x-raw(memory:NVMM), width={W}, height={H}, framerate=30/1 ! "
    "nvvidconv ! video/x-raw, format=BGRx ! "
    "videoconvert ! video/x-raw, format=BGR ! "
    "appsink name=sink max-buffers=1 drop=true sync=false"
)
disp_pipe = Gst.parse_launch(
    "appsrc name=src format=time is-live=true "
    f"caps=video/x-raw,format=BGR,width={W},height={H},framerate=30/1 ! "
    "videoconvert ! autovideosink sync=false"
)

sink = cap_pipe.get_by_name('sink')
src  = disp_pipe.get_by_name('src')
cap_pipe.set_state(Gst.State.PLAYING)
disp_pipe.set_state(Gst.State.PLAYING)
time.sleep(2)

frame_n   = 0
last_dets = []

try:
    while True:
        sample = sink.emit('pull-sample')
        if sample is None:
            time.sleep(0.005)
            continue
        buf  = sample.get_buffer()
        ok, mi = buf.map(Gst.MapFlags.READ)
        if not ok:
            continue
        frame = np.frombuffer(mi.data, dtype=np.uint8).reshape((H, W, 3)).copy()
        buf.unmap(mi)

        if frame_n % 3 == 0:
            with torch.no_grad():
                pred = model(preprocess(frame))
            last_dets = postprocess(pred, H, W)
            if last_dets:
                names = [f"{CLASS_NAMES[c]} {cf:.0%}" for _,_,_,_,cf,c in last_dets]
                print(f"\r偵測到: {', '.join(names)}    ", end='', flush=True)

        display = draw(frame.copy(), last_dets)
        gst_buf = Gst.Buffer.new_wrapped(display.tobytes())
        src.emit('push-buffer', gst_buf)
        frame_n += 1

except KeyboardInterrupt:
    print("\nStopping...")
finally:
    cap_pipe.set_state(Gst.State.NULL)
    disp_pipe.set_state(Gst.State.NULL)
    print("Done.")
