"""
scripts/build_dataset.py — 從 Open Images V7 建立均衡 6 類垃圾資料集
智慧零接觸垃圾分類系統

每個類別獨立下載，確保數量均衡，避免舊版 4 類混用問題。

使用方式：
  python scripts/build_dataset.py               # 預設每類 350 train / 88 val
  python scripts/build_dataset.py --train 500   # 較大資料集
  python scripts/build_dataset.py --dry-run     # 只印計畫，不下載
"""

import argparse
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from config import WASTE_CLASSES

# ── Open Images V7 標籤 → 本系統 class_id ───────────────────────────────
# 每個 class_id 可對應多個 OI 標籤，下載後會合併
OI_CLASS_MAP: dict[int, list[str]] = {
    0: ["Bottle"],           # 寶特瓶（OI: Bottle）
    1: ["Tin can"],          # 鐵鋁罐（OI: Tin can）
    2: ["Box"],              # 紙餐盒（OI: Box — 包含紙箱、紙餐盒）
    3: ["Plastic bag"],      # 塑膠袋（OI: Plastic bag）
    4: ["Juice"],            # 鋁箔包（OI 無 tetra pak，用 Juice 近似）
    5: ["Waste container"],  # 一般垃圾（OI: Waste container）
}

# ── OI 標籤 → class_id（反向查表，供轉換使用）────────────────────────────
_OI_LABEL_TO_CID: dict[str, int] = {
    label: cid
    for cid, labels in OI_CLASS_MAP.items()
    for label in labels
}


def _ensure_fiftyone() -> None:
    try:
        import fiftyone       # noqa: F401
        import fiftyone.zoo   # noqa: F401
    except ImportError:
        sys.exit("請先安裝 fiftyone：pip install fiftyone")


def _download_class(
    cid: int,
    oi_labels: list[str],
    split: str,
    n: int,
    cache: dict,
) -> list[dict]:
    """
    下載指定 OI 標籤的圖片，回傳已轉換的 YOLO 標注列表。
    cache 避免重複下載相同標籤。
    """
    import fiftyone.zoo as foz
    import cv2

    samples_out = []
    per_label   = max(1, n // len(oi_labels))

    for label in oi_labels:
        key = (label, split, per_label)
        if key in cache:
            dataset = cache[key]
        else:
            dataset_name = f"_build_{label.replace(' ', '_')}_{split}_{per_label}"
            try:
                # overwrite=False：重複執行時直接用快取，不重下 4.8GB metadata
                dataset = foz.load_zoo_dataset(
                    "open-images-v7",
                    split=split,
                    label_types=["detections"],
                    classes=[label],
                    max_samples=per_label,
                    dataset_name=dataset_name,
                    overwrite=False,
                )
                cache[key] = dataset
                print(f"    [{label}] 取得 {len(dataset)} 張")
            except Exception as e:
                print(f"    [{label}] 下載失敗：{e}")
                continue

        for sample in dataset:
            img_path = Path(sample.filepath)
            if not img_path.exists():
                continue
            detections = sample.ground_truth
            if detections is None:
                continue

            # 取得圖片尺寸
            if sample.metadata is not None and sample.metadata.width:
                W, H = sample.metadata.width, sample.metadata.height
            else:
                img = cv2.imread(str(img_path))
                if img is None:
                    continue
                H, W = img.shape[:2]

            lines = []
            for det in detections.detections:
                if det.label not in _OI_LABEL_TO_CID:
                    continue
                det_cid = _OI_LABEL_TO_CID[det.label]
                x1, y1, bw, bh = det.bounding_box
                cx = max(0.0, min(1.0, x1 + bw / 2))
                cy = max(0.0, min(1.0, y1 + bh / 2))
                bw = max(0.001, min(1.0, bw))
                bh = max(0.001, min(1.0, bh))
                lines.append(f"{det_cid} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}")

            if lines:
                samples_out.append({"img_path": img_path, "lines": lines})

    return samples_out


def _write_samples(
    samples: list[dict],
    out_dir: Path,
    split: str,
    limit: int,
) -> int:
    img_dir = out_dir / split / "images"
    lbl_dir = out_dir / split / "labels"
    img_dir.mkdir(parents=True, exist_ok=True)
    lbl_dir.mkdir(parents=True, exist_ok=True)

    written = 0
    for s in samples[:limit]:
        img_path: Path = s["img_path"]
        dst_img = img_dir / img_path.name
        # 若有衝突（不同類別同檔名），加前綴
        if dst_img.exists():
            dst_img = img_dir / f"_{written}_{img_path.name}"
        shutil.copy2(img_path, dst_img)
        (lbl_dir / dst_img.stem).with_suffix(".txt").write_text(
            "\n".join(s["lines"]) + "\n", encoding="utf-8"
        )
        written += 1
    return written


def _write_data_yaml(out_dir: Path) -> Path:
    led_zh = {"green": "綠燈", "yellow": "黃燈", "blue": "藍燈",
               "white": "白燈", "orange": "橘燈", "red": "紅燈"}
    nc    = len(WASTE_CLASSES)
    lines = "\n".join(
        f"  {cid}: {info['en'].replace(' ', '_'):<22}# {info['zh']}  → {led_zh.get(info['led'], info['led'])}"
        for cid, info in sorted(WASTE_CLASSES.items())
    )
    content = (
        "# data.yaml — 由 build_dataset.py 自動產生\n"
        f"path: {out_dir.resolve()}\n"
        "train: train/images\n"
        "val:   valid/images\n\n"
        f"nc: {nc}\n"
        f"names:\n{lines}\n"
    )
    yaml_path = out_dir / "data.yaml"
    yaml_path.write_text(content, encoding="utf-8")
    return yaml_path


def _print_distribution(out_dir: Path) -> None:
    counts: dict[int, int] = {cid: 0 for cid in WASTE_CLASSES}
    for lbl in out_dir.rglob("labels/**/*.txt"):
        for line in lbl.read_text(encoding="utf-8").splitlines():
            if line.strip():
                cid = int(line.split()[0])
                counts[cid] = counts.get(cid, 0) + 1
    total = sum(counts.values())
    print("\n  類別分布（bbox 標注數）：")
    for cid, info in sorted(WASTE_CLASSES.items()):
        n   = counts.get(cid, 0)
        pct = n / total * 100 if total else 0
        bar = "█" * int(pct / 2)
        flag = " ⚠️  樣本不足" if n < 100 else ""
        print(f"  [{cid}] {info['zh']:<5} {n:>4} ({pct:4.1f}%) {bar}{flag}")


def build(out_dir: Path, n_train: int, n_val: int, dry_run: bool) -> None:
    print("=" * 60)
    print("  Open Images V7 垃圾資料集建置（6 類均衡）")
    print(f"  目標：每類 {n_train} train / {n_val} val")
    print(f"  輸出：{out_dir.resolve()}")
    print("=" * 60)

    if dry_run:
        print("\n[dry-run] 計劃下載：")
        for cid, labels in OI_CLASS_MAP.items():
            info = WASTE_CLASSES[cid]
            print(f"  [{cid}] {info['zh']} ← OI: {labels}  ({n_train}/{n_val})")
        return

    _ensure_fiftyone()
    import fiftyone as fo

    # 清空舊資料（Windows/OneDrive 有時需要先清除唯讀屬性）
    if out_dir.exists():
        print(f"\n清除舊資料集：{out_dir}")
        import stat, os
        def _force_remove(func, path, _):
            try:
                os.chmod(path, stat.S_IWRITE)
                func(path)
            except Exception:
                pass
        shutil.rmtree(out_dir, onerror=_force_remove)

    cache: dict = {}
    t0 = time.time()

    for split, n_target in [("train", n_train), ("validation", n_val)]:
        out_split = "valid" if split == "validation" else "train"
        print(f"\n── {split.upper()} (目標每類 {n_target} 張) ──────────────────")

        for cid, oi_labels in OI_CLASS_MAP.items():
            info = WASTE_CLASSES[cid]
            print(f"  [{cid}] {info['zh']} ({info['en']})  ← {oi_labels}")
            samples = _download_class(cid, oi_labels, split, n_target, cache)
            written = _write_samples(samples, out_dir, out_split, n_target)
            print(f"    → 寫入 {written} 張")

    # 清理 fiftyone 暫存資料集
    try:
        for ds in list(fo.list_datasets()):
            if ds.startswith("_build_"):
                fo.delete_dataset(ds, verbose=False)
    except Exception:
        pass

    yaml_path = _write_data_yaml(out_dir)
    elapsed   = time.time() - t0

    n_train_imgs = len(list((out_dir / "train" / "images").glob("*"))) if (out_dir / "train" / "images").exists() else 0
    n_val_imgs   = len(list((out_dir / "valid" / "images").glob("*"))) if (out_dir / "valid" / "images").exists() else 0

    print("\n" + "=" * 60)
    print(f"  [OK] 資料集建置完成  ({elapsed/60:.1f} 分鐘)")
    print(f"  Train : {n_train_imgs} 張")
    print(f"  Val   : {n_val_imgs} 張")
    print(f"  data.yaml: {yaml_path}")
    _print_distribution(out_dir)
    print("\n  下一步：python train.py")
    print("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="從 Open Images V7 建立均衡 6 類垃圾資料集"
    )
    parser.add_argument("--train",   type=int, default=350, help="每類 train 目標張數（預設 350）")
    parser.add_argument("--val",     type=int, default=88,  help="每類 val   目標張數（預設 88）")
    parser.add_argument("--out",     default="dataset",     help="輸出目錄（預設 dataset/）")
    parser.add_argument("--dry-run", action="store_true",   help="只印計畫，不下載")
    args = parser.parse_args()

    build(
        out_dir  = Path(args.out),
        n_train  = args.train,
        n_val    = args.val,
        dry_run  = args.dry_run,
    )


if __name__ == "__main__":
    main()
