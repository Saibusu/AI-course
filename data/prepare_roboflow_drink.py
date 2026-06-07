"""
Roboflow 'drink' dataset → YOLO 6-class format converter
Maps:  drink → Class 4 (鋁箔包)
Skips: sign  (not relevant to our 6-class system)

Usage:
  python data/prepare_roboflow_drink.py \
    --input-dir  data/roboflow_drink \
    --output-dir data/foil_yolo
"""

import os
import shutil
import argparse
import yaml
from pathlib import Path
from collections import defaultdict

TARGET_CLASS = 4  # 鋁箔包
CLASS_NAMES = ["寶特瓶", "鐵鋁罐", "紙餐盒", "塑膠袋", "鋁箔包", "一般垃圾"]


def find_drink_class_id(data_yaml_path: Path) -> int:
    with open(data_yaml_path, encoding="utf-8") as f:
        meta = yaml.safe_load(f)
    names = meta.get("names", {})
    # names 可能是 list 或 dict
    if isinstance(names, list):
        for i, name in enumerate(names):
            if "drink" in name.lower():
                return i
    elif isinstance(names, dict):
        for k, v in names.items():
            if "drink" in v.lower():
                return int(k)
    raise ValueError(f"找不到 'drink' 類別，data.yaml 內容：{names}")


def convert(input_dir: str, output_dir: str) -> None:
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)

    data_yaml = input_dir / "data.yaml"
    if not data_yaml.exists():
        raise FileNotFoundError(f"找不到 data.yaml：{data_yaml}")

    drink_id = find_drink_class_id(data_yaml)
    print(f"Roboflow 'drink' class_id = {drink_id} → 映射到 Class {TARGET_CLASS}（鋁箔包）")

    for split in ("train", "val", "test"):
        (output_dir / split / "images").mkdir(parents=True, exist_ok=True)
        (output_dir / split / "labels").mkdir(parents=True, exist_ok=True)

    # Roboflow 用 valid/ 而非 val/
    SPLIT_MAP = {"train": "train", "valid": "val", "test": "test"}
    counters = defaultdict(int)
    skipped = 0

    for rf_split, our_split in SPLIT_MAP.items():
        img_dir = input_dir / rf_split / "images"
        lbl_dir = input_dir / rf_split / "labels"
        if not img_dir.exists():
            continue

        for img_path in img_dir.glob("*.[jJpP][pPnN][gG]"):
            lbl_path = lbl_dir / (img_path.stem + ".txt")
            if not lbl_path.exists():
                skipped += 1
                continue

            new_lines = []
            with open(lbl_path) as f:
                for line in f:
                    parts = line.strip().split()
                    if not parts:
                        continue
                    cls_id = int(parts[0])
                    if cls_id == drink_id:
                        new_lines.append(f"{TARGET_CLASS} {' '.join(parts[1:])}\n")
                        counters[TARGET_CLASS] += 1
                    # sign 或其他類別 → 跳過

            if not new_lines:
                skipped += 1
                continue

            dst_img = output_dir / our_split / "images" / img_path.name
            dst_lbl = output_dir / our_split / "labels" / (img_path.stem + ".txt")
            shutil.copy2(img_path, dst_img)
            with open(dst_lbl, "w") as f:
                f.writelines(new_lines)

    _write_data_yaml(output_dir)

    print(f"\nRoboflow drink 轉換完成。Output: {output_dir}")
    print(f"  Class 4（鋁箔包）：{counters[TARGET_CLASS]} instances")
    print(f"  跳過（無 drink 標註）：{skipped} 張")
    for split in ("train", "val", "test"):
        n = len(list((output_dir / split / "images").glob("*")))
        print(f"  {split}: {n} images")


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
    p.add_argument("--input-dir",  default="data/roboflow_drink")
    p.add_argument("--output-dir", default="data/foil_yolo")
    args = p.parse_args()
    convert(args.input_dir, args.output_dir)
