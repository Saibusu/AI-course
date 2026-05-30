"""
YOLOE-11s fine-tune script
Usage (PC/Colab): python data/train.py --data data/dataset/data.yaml --epochs 50
"""

import argparse
from ultralytics import YOLO


def train(data_yaml: str, epochs: int, imgsz: int, batch: int, device: str) -> None:
    model = YOLO("yolo26s-seg.pt")  # YOLO26 small-seg, auto-downloaded by ultralytics

    results = model.train(
        data=data_yaml,
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        device=device,
        project="runs/train",
        name="waste_sorter",
        exist_ok=True,
        patience=15,
        lr0=1e-3,
        lrf=1e-2,
        mosaic=1.0,
        flipud=0.0,
        fliplr=0.5,
        degrees=15.0,
        translate=0.1,
        scale=0.3,
        hsv_h=0.015,
        hsv_s=0.7,
        hsv_v=0.4,
    )
    print(f"\nTraining done. Best weights: {results.save_dir}/weights/best.pt")
    print(f"Val mAP@50: {results.results_dict.get('metrics/mAP50(B)', 'N/A'):.4f}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--data",   default="data/merged/data.yaml")
    p.add_argument("--epochs", type=int, default=50)
    p.add_argument("--imgsz",  type=int, default=416)
    p.add_argument("--batch",  type=int, default=16)
    p.add_argument("--device", default="0", help="cuda device (0) or cpu")
    args = p.parse_args()
    train(args.data, args.epochs, args.imgsz, args.batch, args.device)
