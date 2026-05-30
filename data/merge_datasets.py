"""
Merge TACO + TrashNet + Roboflow custom into one unified YOLO dataset.
Usage:
  python data/merge_datasets.py \
    --taco    data/dataset \
    --trashnet data/trashnet_yolo \
    --custom  data/custom_roboflow \
    --output  data/merged
"""

import os
import shutil
import argparse
import random
from pathlib import Path

CLASS_NAMES = ["寶特瓶", "鐵鋁罐", "紙餐盒", "塑膠袋", "鋁箔包", "一般垃圾"]


def merge(sources: list[tuple[str, str]], output_dir: str, seed: int = 42) -> None:
    random.seed(seed)
    output_dir = Path(output_dir)

    for split in ("train", "val", "test"):
        (output_dir / split / "images").mkdir(parents=True, exist_ok=True)
        (output_dir / split / "labels").mkdir(parents=True, exist_ok=True)

    total = 0
    for src_name, src_path in sources:
        src = Path(src_path)
        if not src.exists():
            print(f"  [SKIP] {src_name}: {src} not found")
            continue

        count = 0
        for split in ("train", "val", "test"):
            img_dir = src / split / "images"
            lbl_dir = src / split / "labels"
            if not img_dir.exists():
                continue
            for img in img_dir.glob("*.[jJpP][pPnN][gG]"):
                lbl = lbl_dir / (img.stem + ".txt")
                dst_img = output_dir / split / "images" / f"{src_name}_{img.name}"
                dst_lbl = output_dir / split / "labels" / f"{src_name}_{img.stem}.txt"
                shutil.copy2(img, dst_img)
                if lbl.exists():
                    shutil.copy2(lbl, dst_lbl)
                count += 1

        print(f"  {src_name}: {count} images merged")
        total += count

    print(f"\nTotal merged: {total} images → {output_dir}")
    _write_data_yaml(output_dir)


def _write_data_yaml(output_dir: Path) -> None:
    content = f"""path: {output_dir.resolve()}
train: train/images
val:   val/images
test:  test/images

nc: 6
names:
  0: 寶特瓶
  1: 鐵鋁罐
  2: 紙餐盒
  3: 塑膠袋
  4: 鋁箔包
  5: 一般垃圾
"""
    path = output_dir / "data.yaml"
    path.write_text(content, encoding="utf-8")
    print(f"data.yaml written: {path}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--taco",      default="data/dataset",         help="TACO YOLO output dir")
    p.add_argument("--trashnet",  default="data/trashnet_yolo",   help="TrashNet YOLO output dir")
    p.add_argument("--custom",    default="data/custom_roboflow", help="Roboflow custom dir")
    p.add_argument("--output",    default="data/merged",          help="Merged output dir")
    args = p.parse_args()

    sources = [
        ("taco",     args.taco),
        ("trashnet", args.trashnet),
        ("custom",   args.custom),
    ]
    merge(sources, args.output)
