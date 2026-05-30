"""
TrashNet Dataset → YOLO 6-class format converter
TrashNet 為分類資料集（無 bbox），以全圖作為 bbox 轉換。

Usage:
  # 1. Download TrashNet
  #    https://github.com/garythung/trashnet
  #    解壓後結構：data/TrashNet/dataset-resized/{cardboard,glass,metal,paper,plastic,trash}/
  python data/prepare_trashnet.py --trashnet-dir data/TrashNet --output-dir data/trashnet_yolo
"""

import os
import shutil
import argparse
import random
from pathlib import Path
from collections import defaultdict

# TrashNet folder name → 本專案 class_id
# plastic/ 同時含寶特瓶和塑膠袋，依 random 50/50 分配（無法從外觀判斷時的保守策略）
TRASHNET_MAP = {
    "metal":     1,  # 鐵鋁罐
    "paper":     2,  # 紙餐盒
    "cardboard": 2,  # 紙餐盒
    "glass":     5,  # 一般垃圾（玻璃瓶非本專案 6 類，歸入一般）
    "trash":     5,  # 一般垃圾
}
PLASTIC_CLASSES = [0, 3]  # 寶特瓶 / 塑膠袋，50/50 random split

CLASS_NAMES = ["寶特瓶", "鐵鋁罐", "紙餐盒", "塑膠袋", "鋁箔包", "一般垃圾"]


def convert(trashnet_dir: str, output_dir: str, seed: int = 42) -> None:
    random.seed(seed)
    trashnet_dir = Path(trashnet_dir)
    output_dir = Path(output_dir)

    # TrashNet 解壓後有兩種可能的結構
    dataset_dir = trashnet_dir / "dataset-resized"
    if not dataset_dir.exists():
        dataset_dir = trashnet_dir  # fallback: 直接放在根目錄

    for split in ("train", "val", "test"):
        (output_dir / split / "images").mkdir(parents=True, exist_ok=True)
        (output_dir / split / "labels").mkdir(parents=True, exist_ok=True)

    counters = defaultdict(int)
    all_items = []  # (src_path, class_id)

    for folder in dataset_dir.iterdir():
        if not folder.is_dir():
            continue
        folder_name = folder.name.lower()

        if folder_name == "plastic":
            cls_list = PLASTIC_CLASSES
        else:
            cls_id = TRASHNET_MAP.get(folder_name)
            if cls_id is None:
                print(f"  Skipping unknown folder: {folder_name}")
                continue
            cls_list = [cls_id]

        for img_path in folder.glob("*.jpg"):
            cls_id = random.choice(cls_list)
            all_items.append((img_path, cls_id))

    random.shuffle(all_items)
    n = len(all_items)
    split_idx = {"train": int(n * 0.7), "val": int(n * 0.9)}

    for i, (img_path, cls_id) in enumerate(all_items):
        if i < split_idx["train"]:
            split = "train"
        elif i < split_idx["val"]:
            split = "val"
        else:
            split = "test"

        dst_img = output_dir / split / "images" / img_path.name
        shutil.copy2(img_path, dst_img)

        label_file = output_dir / split / "labels" / (img_path.stem + ".txt")
        with open(label_file, "w") as lf:
            lf.write(f"{cls_id} 0.500000 0.500000 1.000000 1.000000\n")

        counters[cls_id] += 1

    print(f"\nTrashNet conversion complete. Output: {output_dir}")
    print(f"Total images: {n}")
    for cls_id, cnt in sorted(counters.items()):
        print(f"  Class {cls_id} ({CLASS_NAMES[cls_id]}): {cnt}")

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
    (output_dir / "data.yaml").write_text(content, encoding="utf-8")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--trashnet-dir", default="data/TrashNet")
    p.add_argument("--output-dir",   default="data/trashnet_yolo")
    p.add_argument("--seed",         type=int, default=42)
    args = p.parse_args()
    convert(args.trashnet_dir, args.output_dir, args.seed)
