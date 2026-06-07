"""
scripts/prepare_openimages.py
從 Open Images V7（公開、免登入）下載廢棄物相關類別，
轉換為 YOLO 格式並寫出 dataset/data.yaml。

6 類對應的 Open Images 標籤：
  寶特瓶  → Bottle
  鐵鋁罐  → Tin can
  紙餐盒  → Cardboard / Box / Paper bag
  塑膠袋  → Plastic bag
  鋁箔包  → Juice box（Open Images 覆蓋率有限，以 Carton 補充）
  一般垃圾 → Waste container

注意：Open Images 中沒有專門的「鋁箔包」標籤；
      Juice box / Carton 是最接近的替代，建議搭配 Roboflow TACO 資料集增補。

使用方式：
  python scripts/prepare_openimages.py
  python scripts/prepare_openimages.py --samples 600   # 每類最多 N 張
"""

import argparse
import shutil
import sys
from pathlib import Path

# ── 類別映射：Open Images 標籤 → 本系統 class_id ─────────────────────────
#
#   0: PET_Bottle       (寶特瓶  → 綠燈)
#   1: Aluminum_Can     (鐵鋁罐  → 黃燈)
#   2: Paper_Container  (紙餐盒  → 藍燈)
#   3: Plastic_Bag      (塑膠袋  → 白燈)
#   4: Foil_Package     (鋁箔包  → 橘燈)  ← Juice box / Carton 替代
#   5: General_Waste    (一般垃圾 → 紅燈)
OI_TO_CLASS: dict[str, int] = {
    "Bottle":           0,   # 寶特瓶 / 塑膠瓶
    "Tin can":          1,   # 鐵鋁罐
    "Cardboard":        2,   # 紙餐盒（紙箱）
    "Paper bag":        2,   # 紙袋
    "Plastic bag":      3,   # 塑膠袋
    "Juice box":        4,   # 鋁箔包（果汁盒）
    "Carton":           4,   # 鋁箔包（牛奶盒等）
    "Waste container":  5,   # 一般垃圾（垃圾桶/袋）
}
CLASSES = list(OI_TO_CLASS.keys())


def _build_data_yaml(out_dir: Path) -> str:
    """動態從 config.WASTE_CLASSES 生成 data.yaml，確保與系統設定同步。"""
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from config import WASTE_CLASSES

    led_zh = {"green": "綠燈", "yellow": "黃燈", "blue": "藍燈",
               "white": "白燈", "orange": "橘燈", "red": "紅燈"}
    nc = len(WASTE_CLASSES)
    names_lines = "\n".join(
        f"  {cid}: {info['en'].replace(' ', '_'):<22}# {info['zh']}  → {led_zh.get(info['led'], info['led'])}"
        for cid, info in sorted(WASTE_CLASSES.items())
    )
    return (
        "# dataset/data.yaml — Open Images V7 廢棄物子集（自動產生）\n"
        f"path: {out_dir.resolve()}\n"
        "train: train/images\n"
        "val:   val/images\n\n"
        f"nc: {nc}\n"
        f"names:\n{names_lines}\n"
    )


def _ensure_fiftyone() -> None:
    try:
        import fiftyone       # noqa: F401
        import fiftyone.zoo   # noqa: F401
    except ImportError:
        sys.exit(
            "請先安裝 fiftyone：\n"
            "  pip install fiftyone\n"
            "注意：fiftyone 需要額外約 2 GB 磁碟空間。"
        )


def download_split(split: str, max_samples: int):
    import fiftyone.zoo as foz
    print(f"\n[{split}] 下載 Open Images V7（每類最多 {max_samples} 張）…")
    dataset = foz.load_zoo_dataset(
        "open-images-v7",
        split=split,
        label_types=["detections"],
        classes=CLASSES,
        max_samples=max_samples,
        dataset_name=f"oi_waste_{split}_{max_samples}",
        overwrite=True,
    )
    print(f"  已取得 {len(dataset)} 張圖片（含多類別）")
    return dataset


def export_yolo(dataset, out_dir: Path, split: str) -> tuple[int, int]:
    import cv2

    img_dir = out_dir / split / "images"
    lbl_dir = out_dir / split / "labels"
    img_dir.mkdir(parents=True, exist_ok=True)
    lbl_dir.mkdir(parents=True, exist_ok=True)

    converted = skipped = 0
    for sample in dataset:
        img_path = Path(sample.filepath)
        if not img_path.exists():
            skipped += 1
            continue

        # 取圖片尺寸
        if sample.metadata is not None and sample.metadata.width:
            W, H = sample.metadata.width, sample.metadata.height
        else:
            img = cv2.imread(str(img_path))
            if img is None:
                skipped += 1
                continue
            H, W = img.shape[:2]

        detections = sample.ground_truth
        if detections is None:
            skipped += 1
            continue

        lines = []
        for det in detections.detections:
            oi_label = det.label
            if oi_label not in OI_TO_CLASS:
                continue
            new_id = OI_TO_CLASS[oi_label]

            # Open Images bbox = [left, top, width, height] 相對座標
            x1, y1, bw, bh = det.bounding_box
            cx = max(0.0, min(1.0, x1 + bw / 2))
            cy = max(0.0, min(1.0, y1 + bh / 2))
            bw = max(0.001, min(1.0, bw))
            bh = max(0.001, min(1.0, bh))
            lines.append(f"{new_id} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}")

        if not lines:
            skipped += 1
            continue

        shutil.copy2(img_path, img_dir / img_path.name)
        (lbl_dir / img_path.stem).with_suffix(".txt").write_text(
            "\n".join(lines) + "\n", encoding="utf-8"
        )
        converted += 1

    print(f"  [{split}] 轉換：{converted} 張，略過（無標注）：{skipped} 張")
    return converted, skipped


def _log_class_distribution(out_dir: Path) -> None:
    """印出各類別在資料集中的標注數量。"""
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from config import WASTE_CLASSES

    counts: dict[int, int] = {cid: 0 for cid in WASTE_CLASSES}
    for lbl in out_dir.rglob("labels/**/*.txt"):
        for line in lbl.read_text(encoding="utf-8").splitlines():
            if line.strip():
                cid = int(line.split()[0])
                counts[cid] = counts.get(cid, 0) + 1
    total = sum(counts.values())
    print("\n類別分布（bbox 數量）：")
    for cid, info in sorted(WASTE_CLASSES.items()):
        n   = counts.get(cid, 0)
        pct = n / total * 100 if total else 0
        bar = "█" * int(pct / 2)
        print(f"  [{cid}] {info['zh']}（{info['en']:<18}) {n:>5} ({pct:5.1f}%)  {bar}")
    if counts.get(4, 0) < 50:
        print("\n  ⚠️  鋁箔包 (class 4) 樣本較少，建議補充 Roboflow TACO 資料集：")
        print("       python scripts/download_dataset.py --key YOUR_KEY")


def main():
    parser = argparse.ArgumentParser(description="Open Images V7 廢棄物資料集下載工具（6 類）")
    parser.add_argument("--samples", type=int, default=500,
                        help="每個類別最多下載幾張 train（預設 500）")
    parser.add_argument("--out", default="dataset",
                        help="輸出目錄（預設：dataset/）")
    args = parser.parse_args()

    _ensure_fiftyone()
    import fiftyone as fo

    out_dir = Path(args.out)

    print("=" * 58)
    print("  Open Images V7 廢棄物資料集下載（6 類）")
    print(f"  Open Images 標籤：{CLASSES}")
    print(f"  每類最多 {args.samples} 張（train），{args.samples // 4} 張（val）")
    print(f"  輸出：{out_dir.resolve()}")
    print("=" * 58)

    try:
        train_ds = download_split("train",      args.samples)
        val_ds   = download_split("validation", args.samples // 4)

        print("\n轉換為 YOLO 格式…")
        export_yolo(train_ds, out_dir, "train")
        export_yolo(val_ds,   out_dir, "val")

        n_train = len(list((out_dir / "train" / "images").glob("*")))
        n_val   = len(list((out_dir / "val"   / "images").glob("*")))

        data_yaml = out_dir / "data.yaml"
        data_yaml.write_text(_build_data_yaml(out_dir), encoding="utf-8")

        _log_class_distribution(out_dir)

        print("=" * 58)
        print(f"  [OK] 資料集就緒")
        print(f"  Train : {n_train} 張")
        print(f"  Val   : {n_val} 張")
        print(f"  data.yaml: {data_yaml}")
        print()
        print("  下一步：python train.py")
        print("=" * 58)

    finally:
        try:
            fo.delete_dataset(f"oi_waste_train_{args.samples}", verbose=False)
            fo.delete_dataset(f"oi_waste_validation_{args.samples // 4}", verbose=False)
        except Exception:
            pass


if __name__ == "__main__":
    main()
