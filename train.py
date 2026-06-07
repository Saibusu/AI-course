"""
train.py — 訓練廢棄物分類 YOLO26 模型
智慧零接觸垃圾分類系統 | Jetson Orin Nano

使用方式：
  # 先下載資料集（需 Roboflow API Key）
  python scripts/download_dataset.py --key YOUR_API_KEY

  # 開始訓練
  python train.py

  # 自訂參數
  python train.py --data dataset/data.yaml --epochs 100 --batch 8

  # CPU 訓練（無 GPU）
  python train.py --device cpu

資料集目錄結構（Roboflow / ultralytics YOLOv8 格式）：
  dataset/
  ├── data.yaml          ← 由 scripts/download_dataset.py 自動產生
  ├── train/
  │   ├── images/
  │   └── labels/
  ├── valid/
  │   ├── images/
  │   └── labels/
  └── test/（選填）
      ├── images/
      └── labels/
"""

import argparse
import logging
import shutil
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# LED 顏色對應的中文說明（僅用於 data.yaml 範本的註解）
_LED_ZH = {"green": "綠燈", "yellow": "黃燈", "blue": "藍燈",
           "white": "白燈", "orange": "橘燈", "red": "紅燈"}


def _build_yaml_template() -> str:
    """從 config.WASTE_CLASSES 動態產生 data.yaml 範本，確保與系統設定同步。"""
    from config import WASTE_CLASSES
    nc = len(WASTE_CLASSES)
    names_lines = "\n".join(
        f"  {cid}: {info['en'].replace(' ', '_'):<20} # {info['zh']}  → {_LED_ZH.get(info['led'], info['led'])}"
        for cid, info in sorted(WASTE_CLASSES.items())
    )
    return (
        "# data.yaml — 廢棄物分類資料集描述\n"
        "# 由 scripts/download_dataset.py 自動產生，或手動建立\n\n"
        "path: dataset\n"
        "train: train/images\n"
        "val:   valid/images\n\n"
        f"nc: {nc}\n"
        f"names:\n{names_lines}\n"
    )


def _check_dataset(data_yaml: Path) -> None:
    if not data_yaml.exists():
        template = _build_yaml_template()
        logger.warning(f"data.yaml 不存在，建立範本：{data_yaml}")
        data_yaml.parent.mkdir(parents=True, exist_ok=True)
        data_yaml.write_text(template, encoding="utf-8")
        raise SystemExit(
            f"\n{'='*60}\n"
            f"  已建立資料集範本：{data_yaml}\n\n"
            f"  請先下載資料集：\n"
            f"    python scripts/download_dataset.py --key YOUR_ROBOFLOW_KEY\n\n"
            f"  或手動準備資料集後再執行訓練。\n"
            f"  取得免費 API Key：https://roboflow.com（註冊後點 Settings）\n"
            f"{'='*60}"
        )

    import yaml
    from config import WASTE_CLASSES
    with open(data_yaml, encoding="utf-8") as f:
        meta = yaml.safe_load(f)
    nc        = meta.get("nc", 0)
    names     = meta.get("names", {})
    name_list = list(names.values()) if isinstance(names, dict) else names
    expected  = len(WASTE_CLASSES)
    logger.info(f"資料集：{data_yaml}  |  類別數 nc={nc}  |  {name_list}")
    if nc != expected:
        logger.warning(
            f"資料集類別數 nc={nc}，但 config.py 設定為 {expected} 類。\n"
            "  請確認 data.yaml 與 config.py 中的 WASTE_CLASSES 一致。"
        )


def train(
    data_yaml: str,
    epochs: int,
    batch: int,
    imgsz: int,
    device: str,
    model_size: str,
) -> None:
    from ultralytics import YOLO

    data_path = Path(data_yaml)
    _check_dataset(data_path)

    # YOLO26 模型名稱格式：yolo26n / yolo26s / yolo26m / yolo26l / yolo26x
    base_model = f"yolo26{model_size}.pt"

    logger.info(
        f"\n{'='*50}\n"
        f"  開始訓練廢棄物分類模型（YOLO26）\n"
        f"  基底模型：{base_model}\n"
        f"  資料集  ：{data_path}\n"
        f"  Epochs  ：{epochs}\n"
        f"  Batch   ：{batch}\n"
        f"  imgsz   ：{imgsz}\n"
        f"  Device  ：{device}\n"
        f"{'='*50}"
    )

    model = YOLO(base_model)

    # YOLO26 使用 MuSGD 優化器，不需手動指定 SGD 參數
    # end-to-end NMS-free 架構，不需額外後處理調整
    model.train(
        data=str(data_path),
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        device=device,
        project="runs/detect",
        name="waste_classifier",
        exist_ok=True,
        pretrained=True,
        patience=30,
        save=True,
        plots=True,
        verbose=True,
        # YOLO26 推薦增強參數
        hsv_h=0.015,
        hsv_s=0.7,
        hsv_v=0.4,
        translate=0.1,
        scale=0.5,
        fliplr=0.5,
        mosaic=1.0,
    )

    # 搜尋 best.pt（ultralytics 版本間路徑結構略有不同）
    candidates = sorted(
        Path("runs").rglob("best.pt"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError(
            "訓練完成但找不到 best.pt，請手動確認 runs/ 目錄下的模型位置。"
        )
    best = candidates[0]

    dst = Path("models/waste_classifier.pt")
    dst.parent.mkdir(exist_ok=True)
    shutil.copy2(best, dst)

    logger.info(
        f"\n{'='*50}\n"
        f"  ✅ 訓練完成！\n"
        f"  最佳模型：{best}\n"
        f"  已複製至：{dst}\n\n"
        f"  後續步驟：\n"
        f"  1. PC 驗證：python main.py\n"
        f"  2. 複製 models/waste_classifier.pt 至 Jetson\n"
        f"  3. Jetson 轉換 TensorRT engine：\n"
        f"       python export_tensorrt.py\n"
        f"  4. 啟動系統：\n"
        f"       docker-compose -f docker-compose.jetson.yml up -d\n"
        f"{'='*50}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="訓練廢棄物分類 YOLO26 模型",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--data",   default="dataset/data.yaml",
                        help="資料集 data.yaml 路徑（預設：dataset/data.yaml）")
    parser.add_argument("--epochs", type=int, default=50,
                        help="訓練輪數（預設：50）")
    parser.add_argument("--batch",  type=int, default=16,
                        help="批次大小（預設：16；GPU 記憶體不足時縮小）")
    parser.add_argument("--imgsz",  type=int, default=416,
                        help="輸入解析度（預設：416；需與推論設定一致）")
    parser.add_argument("--device", default="0",
                        help="訓練裝置（預設：0=GPU；cpu=使用 CPU）")
    parser.add_argument("--model",  default="n",
                        choices=["n", "s", "m", "l", "x"],
                        dest="model_size",
                        help="YOLO26 大小（n 最快 / x 最準，預設：n）")
    args = parser.parse_args()

    train(
        data_yaml=args.data,
        epochs=args.epochs,
        batch=args.batch,
        imgsz=args.imgsz,
        device=args.device,
        model_size=args.model_size,
    )


if __name__ == "__main__":
    main()
