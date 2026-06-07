"""
export_tensorrt.py — 將訓練好的 YOLO .pt 模型轉換為 TensorRT FP16 engine
智慧零接觸垃圾分類系統

⚠️  此腳本必須在 Jetson Orin Nano 上執行（TensorRT engine 與硬體綁定）
    PC 上訓練完成後，將 .pt 複製至 Jetson，再執行此腳本。

使用方式：
  python export_tensorrt.py --model models/waste_classifier.pt
  python export_tensorrt.py --model models/waste_classifier.pt --imgsz 416 --batch 1
"""

import argparse
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def export(model_path: str, imgsz: int, batch: int) -> None:
    from ultralytics import YOLO

    src = Path(model_path)
    if not src.exists():
        raise FileNotFoundError(f"找不到模型檔案：{src}")

    logger.info(f"載入模型：{src}")
    model = YOLO(str(src))

    logger.info(f"開始轉換 TensorRT FP16 engine（imgsz={imgsz}, batch={batch}）…")
    logger.info("  這可能需要 5–15 分鐘，請耐心等待。")

    engine_path = model.export(
        format="engine",
        imgsz=imgsz,
        half=True,        # FP16 量化
        batch=batch,
        device=0,         # GPU 0
        workspace=4,      # 4 GB workspace（Orin Nano 適合值）
        verbose=False,
    )

    logger.info(f"✅ TensorRT engine 已產生：{engine_path}")
    logger.info(f"   請將此檔案路徑填入 config.py 的 MODEL_PATH。")

    # 快速驗證：用 engine 跑一次推論
    logger.info("驗證 engine 可正常推論…")
    import numpy as np
    engine_model = YOLO(engine_path)
    dummy = np.zeros((imgsz, imgsz, 3), dtype=np.uint8)
    result = engine_model(dummy, verbose=False)
    logger.info(f"✅ 驗證通過！結果：{result[0].boxes}")


def main():
    parser = argparse.ArgumentParser(description="YOLO → TensorRT FP16 轉換工具")
    parser.add_argument("--model",  default="models/waste_classifier.pt",
                        help=".pt 模型路徑")
    parser.add_argument("--imgsz",  type=int, default=416,
                        help="推論輸入解析度（預設 416）")
    parser.add_argument("--batch",  type=int, default=1,
                        help="batch size（邊緣部署固定為 1）")
    args = parser.parse_args()

    export(args.model, args.imgsz, args.batch)


if __name__ == "__main__":
    main()
