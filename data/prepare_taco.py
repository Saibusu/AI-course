"""
TACO Dataset → YOLO 6-class format converter
Usage: python data/prepare_taco.py --taco-dir data/TACO --output-dir data/dataset
"""

import json
import os
import shutil
import argparse
from pathlib import Path
from collections import defaultdict

# TACO category name → local 6-class index
# Based on TACO's annotations/annotations.json category list
TACO_TO_6CLASS = {
    # 0 寶特瓶 PET bottle
    "Bottle": 0,
    "Plastic bottle cap": 0,
    "Drink carton cap": 0,

    # 1 鐵鋁罐 Metal can
    "Can": 1,
    "Aerosol": 1,
    "Metal bottle cap": 1,

    # 2 紙餐盒 Paper food container
    "Paper cup": 2,
    "Carton": 2,
    "Meal carton": 2,
    "Pizza box": 2,
    "Paper bag": 2,

    # 3 塑膠袋 Plastic bag
    "Plastic bag & wrapper": 3,
    "Six pack rings": 3,
    "Plastic film": 3,
    "Single-use carrier bag": 3,

    # 4 鋁箔包 Foil / Tetra Pak
    "Drink carton": 4,
    "Aluminium foil": 4,

    # 5 一般垃圾 (everything else falls here)
}
DEFAULT_CLASS = 5  # 一般垃圾


def convert(taco_dir: str, output_dir: str) -> None:
    taco_dir = Path(taco_dir)
    output_dir = Path(output_dir)

    ann_path = taco_dir / "annotations" / "annotations.json"
    if not ann_path.exists():
        raise FileNotFoundError(f"TACO annotations not found: {ann_path}")

    with open(ann_path, encoding="utf-8") as f:
        coco = json.load(f)

    # Build lookup maps
    cat_id_to_name = {c["id"]: c["name"] for c in coco["categories"]}
    img_id_to_info = {img["id"]: img for img in coco["images"]}
    img_id_to_anns = defaultdict(list)
    for ann in coco["annotations"]:
        img_id_to_anns[ann["image_id"]].append(ann)

    # Create output split dirs
    for split in ("train", "val", "test"):
        (output_dir / split / "images").mkdir(parents=True, exist_ok=True)
        (output_dir / split / "labels").mkdir(parents=True, exist_ok=True)

    # 70/20/10 split by image id order
    image_ids = list(img_id_to_info.keys())
    n = len(image_ids)
    splits = {
        "train": image_ids[: int(n * 0.7)],
        "val":   image_ids[int(n * 0.7): int(n * 0.9)],
        "test":  image_ids[int(n * 0.9):],
    }

    counters = defaultdict(int)

    for split, ids in splits.items():
        for img_id in ids:
            img_info = img_id_to_info[img_id]
            src_img = taco_dir / img_info["file_name"]
            if not src_img.exists():
                continue

            anns = img_id_to_anns[img_id]
            if not anns:
                continue

            dst_img = output_dir / split / "images" / src_img.name
            shutil.copy2(src_img, dst_img)

            label_file = output_dir / split / "labels" / (src_img.stem + ".txt")
            w, h = img_info["width"], img_info["height"]

            with open(label_file, "w") as lf:
                for ann in anns:
                    cat_name = cat_id_to_name.get(ann["category_id"], "")
                    cls = TACO_TO_6CLASS.get(cat_name, DEFAULT_CLASS)
                    x, y, bw, bh = ann["bbox"]
                    cx = (x + bw / 2) / w
                    cy = (y + bh / 2) / h
                    nw = bw / w
                    nh = bh / h
                    lf.write(f"{cls} {cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}\n")
                    counters[cls] += 1

    print("Conversion complete.")
    print(f"Output: {output_dir}")
    class_names = ["寶特瓶", "鐵鋁罐", "紙餐盒", "塑膠袋", "鋁箔包", "一般垃圾"]
    for cls_id, cnt in sorted(counters.items()):
        print(f"  Class {cls_id} ({class_names[cls_id]}): {cnt} instances")

    _write_data_yaml(output_dir)


def _write_data_yaml(output_dir: Path) -> None:
    yaml_content = f"""path: {output_dir.resolve()}
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
    yaml_path = output_dir / "data.yaml"
    yaml_path.write_text(yaml_content, encoding="utf-8")
    print(f"data.yaml written: {yaml_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--taco-dir",    default="data/TACO",    help="TACO root directory")
    parser.add_argument("--output-dir",  default="data/dataset", help="Output YOLO dataset directory")
    args = parser.parse_args()
    convert(args.taco_dir, args.output_dir)
