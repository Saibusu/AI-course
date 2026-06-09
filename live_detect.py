import os, time
import numpy as np
import cv2

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst

import tensorrt as trt
import pycuda.driver as cuda
import pycuda.autoinit

# 5-class system (v5) — 鋁箔包 removed, 塑膠袋 on Pin 21
CLASS_NAMES  = ['寶特瓶', '鐵鋁罐', '紙餐盒', '塑膠袋', '一般垃圾']
CLASS_LABELS = ['Bottle', 'MetalCan', 'PaperBox', 'Bag', 'General']
COLORS = [
    (0, 255, 0),     # Bottle   — green
    (0, 255, 255),   # MetalCan — yellow
    (255, 0, 0),     # PaperBox — blue
    (200, 200, 200), # Bag      — white
    (0, 0, 255),     # General  — red
]

ENGINE_PATH = os.path.expanduser('~/AI-course/models/best_v5.engine')
CONF_THRESH = 0.55
INPUT_SIZE  = 416
W, H        = 1280, 720
TRT_LOGGER  = trt.Logger(trt.Logger.WARNING)


class TRTYolo:
    """TensorRT inference — pure pycuda, no PyTorch/ultralytics."""

    def __init__(self, engine_path):
        with open(engine_path, 'rb') as f:
            self.engine = trt.Runtime(TRT_LOGGER).deserialize_cuda_engine(f.read())
        self.context = self.engine.create_execution_context()
        self.stream  = cuda.Stream()
        self._setup()

    def _setup(self):
        self.names  = [self.engine.get_tensor_name(i)
                       for i in range(self.engine.num_io_tensors)]
        self.h_bufs = {}
        self.d_bufs = {}
        for name in self.names:
            shape = tuple(abs(s) for s in self.engine.get_tensor_shape(name))
            dtype = trt.nptype(self.engine.get_tensor_dtype(name))
            h = cuda.pagelocked_empty(int(np.prod(shape)), dtype)
            d = cuda.mem_alloc(h.nbytes)
            self.h_bufs[name] = (h, shape)
            self.d_bufs[name] = d
        self.in_name  = next(n for n in self.names
                             if self.engine.get_tensor_mode(n) == trt.TensorIOMode.INPUT)
        self.out_name = next(n for n in self.names
                             if self.engine.get_tensor_mode(n) == trt.TensorIOMode.OUTPUT)

    def infer(self, img_bchw_f32: np.ndarray) -> np.ndarray:
        h_in, _ = self.h_bufs[self.in_name]
        np.copyto(h_in, img_bchw_f32.astype(np.float32).ravel())
        cuda.memcpy_htod_async(self.d_bufs[self.in_name], h_in, self.stream)
        for name in self.names:
            self.context.set_tensor_address(name, int(self.d_bufs[name]))
        self.context.execute_async_v3(self.stream.handle)
        h_out, shape = self.h_bufs[self.out_name]
        cuda.memcpy_dtoh_async(h_out, self.d_bufs[self.out_name], self.stream)
        self.stream.synchronize()
        return np.array(h_out, dtype=np.float32).reshape(shape)


def preprocess(frame: np.ndarray) -> np.ndarray:
    img = cv2.resize(frame, (INPUT_SIZE, INPUT_SIZE))
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    return img.transpose(2, 0, 1)[np.newaxis]   # (1, 3, H, W)


def postprocess(output: np.ndarray, orig_w: int, orig_h: int):
    """
    TRT output: (1, 300, 6) — already TopK filtered.
    Each row: [x1, y1, x2, y2, conf, cls_id] in INPUT_SIZE pixel space.
    """
    preds   = output[0]   # (300, 6)
    scale_x = orig_w / INPUT_SIZE
    scale_y = orig_h / INPUT_SIZE
    results = []
    for row in preds:
        x1, y1, x2, y2, conf, cls_id = row
        if float(conf) < CONF_THRESH:
            continue
        cls_id = int(cls_id)
        if cls_id >= len(CLASS_NAMES):
            continue
        results.append((
            int(x1 * scale_x), int(y1 * scale_y),
            int(x2 * scale_x), int(y2 * scale_y),
            float(conf), cls_id,
        ))
    return results


# ── Load TRT engine ──────────────────────────────────────────────────────────
print("Loading TRT engine (yolo26m FP16, 5-class v5)...")
model = TRTYolo(ENGINE_PATH)
print("Engine loaded. Starting camera pipelines...")

# ── GStreamer pipelines ──────────────────────────────────────────────────────
Gst.init(None)

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
print("Ready — point camera at trash items. Press Ctrl+C to quit.\n")

# ── Main loop ────────────────────────────────────────────────────────────────
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

        buf = sample.get_buffer()
        ok, map_info = buf.map(Gst.MapFlags.READ)
        if not ok:
            continue
        frame = np.frombuffer(map_info.data, dtype=np.uint8).reshape((H, W, 3)).copy()
        buf.unmap(map_info)

        if frame_n % 3 == 0:
            inp  = preprocess(frame)
            out  = model.infer(inp)
            dets = postprocess(out, W, H)

            display = frame.copy()
            if dets:
                for (x1, y1, x2, y2, conf, cls_id) in dets:
                    color = COLORS[cls_id] if cls_id < len(COLORS) else (255, 255, 255)
                    cv2.rectangle(display, (x1, y1), (x2, y2), color, 2)
                    label = f"{CLASS_LABELS[cls_id]} {conf:.0%}"
                    cv2.putText(display, label, (x1, max(y1 - 8, 20)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
                    print(f"\r偵測到: {CLASS_NAMES[cls_id]}  {conf:.1%}    ",
                          end='', flush=True)
            else:
                cv2.putText(display, "---", (20, 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (128, 128, 128), 2)
            last_display = display

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
