"""
scripts/merge_roboflow.py
把已下載的 Roboflow 資料集合併進 dataset/ 目錄

來源：
  1. data/roboflow/tetra_pak_official  — 239 張，class 0(tetra) → 4(鋁箔包)
  2. data/roboflow/can_bottle_pack     — 1650+69 張
       can_*         (id 0-5)  → 1(鐵鋁罐)
       plasticBottle_*(id 6-20) → 0(寶特瓶)
       tetraPack_*   (id 21-22) → 4(鋁箔包)
"""
import shutil, sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

DATASET_DIR = ROOT / "dataset"
RF_DIR      = ROOT / "data" / "roboflow"


def _remap_labels(src_lbl_dir: Path, id_map: dict[int, int]) -> list[tuple[Path, list[str]]]:
    """讀取標注，重映射 class_id，回傳 [(lbl_path, new_lines)]。"""
    result = []
    for lbl in src_lbl_dir.glob("*.txt"):
        lines_out = []
        for line in lbl.read_text(encoding="utf-8").splitlines():
            parts = line.strip().split()
            if len(parts) < 5:
                continue
            orig_id = int(parts[0])
            if orig_id in id_map:
                lines_out.append(f"{id_map[orig_id]} " + " ".join(parts[1:]))
        if lines_out:
            result.append((lbl, lines_out))
    return result


def _copy_to_dataset(src_img_dir: Path, src_lbl_dir: Path,
                     id_map: dict[int, int], split: str, prefix: str) -> int:
    dst_img = DATASET_DIR / split / "images"
    dst_lbl = DATASET_DIR / split / "labels"
    dst_img.mkdir(parents=True, exist_ok=True)
    dst_lbl.mkdir(parents=True, exist_ok=True)

    remapped = _remap_labels(src_lbl_dir, id_map)
    written  = 0
    for lbl_path, lines in remapped:
        img_path = src_img_dir / (lbl_path.stem + ".jpg")
        if not img_path.exists():
            # try other extensions
            for ext in [".jpeg", ".png", ".bmp"]:
                alt = src_img_dir / (lbl_path.stem + ext)
                if alt.exists():
                    img_path = alt
                    break
            else:
                continue

        dst_img_path = dst_img / f"{prefix}_{lbl_path.stem}.jpg"
        dst_lbl_path = dst_lbl / f"{prefix}_{lbl_path.stem}.txt"
        try:
            shutil.copy2(img_path, dst_img_path)
            dst_lbl_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            written += 1
        except Exception:
            pass
    return written


def merge():
    # ── 1. Tetra Pak Official ──────────────────────────────────────────────
    # nc=1, class 0 = tetra → 4
    tp_dir = RF_DIR / "tetra_pak_official"
    tp_map  = {0: 4}
    total_tp = 0
    for split_src, split_dst in [("train", "train"), ("valid", "valid"), ("test", "valid")]:
        img_dir = tp_dir / split_src / "images"
        lbl_dir = tp_dir / split_src / "labels"
        if not img_dir.exists():
            continue
        n = _copy_to_dataset(img_dir, lbl_dir, tp_map, split_dst, f"tp_{split_src}")
        print(f"  Tetra Pak official [{split_src}→{split_dst}]: {n} 張")
        total_tp += n

    # ── 2. Can / Bottle / Pack ─────────────────────────────────────────────
    # id 0-5  : can_*          → 1
    # id 6-20 : plasticBottle_ → 0
    # id 21-22: tetraPack_     → 4
    cbp_dir = RF_DIR / "can_bottle_pack"
    cbp_map: dict[int, int] = {}
    for i in range(0,  6): cbp_map[i] = 1   # 鐵鋁罐
    for i in range(6, 21): cbp_map[i] = 0   # 寶特瓶
    for i in range(21, 23): cbp_map[i] = 4  # 鋁箔包

    total_cbp = 0
    for split_src, split_dst in [("train", "train"), ("valid", "valid")]:
        img_dir = cbp_dir / split_src / "images"
        lbl_dir = cbp_dir / split_src / "labels"
        if not img_dir.exists():
            continue
        n = _copy_to_dataset(img_dir, lbl_dir, cbp_map, split_dst, f"cbp_{split_src}")
        print(f"  Can/Bottle/Pack [{split_src}→{split_dst}]: {n} 張")
        total_cbp += n

    # ── 統計 ───────────────────────────────────────────────────────────────
    from config import WASTE_CLASSES
    counts: dict[int, int] = {cid: 0 for cid in WASTE_CLASSES}
    for lbl in DATASET_DIR.rglob("labels/**/*.txt"):
        for line in lbl.read_text(encoding="utf-8").splitlines():
            if line.strip():
                cid = int(line.split()[0])
                counts[cid] = counts.get(cid, 0) + 1
    total = sum(counts.values())

    print(f"\n  合併完成：Tetra Pak={total_tp}, Can/Bottle/Pack={total_cbp}")
    print(f"  Train: {len(list((DATASET_DIR/'train'/'images').glob('*.*')))} 張")
    print(f"  Valid: {len(list((DATASET_DIR/'valid'/'images').glob('*.*')))} 張")
    print("\n  最終類別分布：")
    for cid, info in sorted(WASTE_CLASSES.items()):
        n   = counts.get(cid, 0)
        pct = n / total * 100 if total else 0
        bar = "#" * int(pct / 2)
        warn = " <-- 不足" if n < 200 else ""
        print(f"  [{cid}] {info['zh']:<5}  {n:>5} ({pct:5.1f}%)  {bar}{warn}")


if __name__ == "__main__":
    merge()
