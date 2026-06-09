"""
scripts/build_dataset_v2.py — 正確且大型的 6 類垃圾資料集建置

資料來源（全部自動下載，無需手動操作）：
  1. Open Images V7 (fiftyone) — 修正後的標籤對應，移除錯誤的 "Juice"
  2. Kaggle: TACO Dataset YOLO Format (vencerlanz09) — 真實垃圾照片
  3. Kaggle: Plastic Object Detection (dataclusterlabs) — 補強塑膠類
  4. 鋁箔包 (class 4)：從 Kaggle household-trash + TACO Drink carton 類別提取

使用方式：
  python scripts/build_dataset_v2.py
  python scripts/build_dataset_v2.py --train 700 --val 175
"""
import argparse, os, shutil, sys, time, zipfile, stat
from pathlib import Path
import requests

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
from config import WASTE_CLASSES

KAGGLE_TOKEN = os.environ.get("KAGGLE_API_TOKEN", "KGAT_976f08fec7958d9229ba8064b1d976fb")
KAGGLE_HEADERS = {"Authorization": f"Bearer {KAGGLE_TOKEN}"}

# ── Open Images V7 標籤（已修正，移除錯誤的 Juice）─────────────────────────
OI_CLASS_MAP = {
    0: ["Bottle"],         # 寶特瓶 — OI Bottle 雖泛，但量多可用
    1: ["Tin can"],        # 鐵鋁罐
    2: ["Box"],            # 紙餐盒
    3: ["Plastic bag"],    # 塑膠袋
    # class 4 (鋁箔包) 從 OI 移除 — "Juice" 標籤是飲料杯，不是鋁箔包
    5: ["Waste container"],# 一般垃圾
}

# ── TACO YOLO 類別精確名稱 → 本系統 class_id ──────────────────────────────
# 使用精確名稱查表，避免 substring 誤判（例如 "Carton" 被 "Meal carton" 吃掉）
# TACO 18 類（vencerlanz09 Kaggle 版）：
#   0:Aluminium foil 1:Bottle cap 2:Bottle 3:Broken glass 4:Can 5:Carton
#   6:Cigarette 7:Cup 8:Lid 9:Other litter 10:Other plastic 11:Paper
#   12:Plastic bag - wrapper 13:Plastic container 14:Pop tab 15:Straw
#   16:Styrofoam piece 17:Unlabeled litter
TACO_NAME_TO_CID: dict[str, int] = {
    "Bottle":               0,   # 寶特瓶
    "Plastic container":    0,   # 寶特瓶（塑膠容器）
    "Aluminium foil":       1,   # 鐵鋁罐
    "Can":                  1,   # 鐵鋁罐
    "Lid":                  1,   # 鐵鋁罐（金屬蓋）
    "Cup":                  2,   # 紙餐盒
    "Paper":                2,   # 紙餐盒
    "Carton":               4,   # 鋁箔包 ← 正確：Tetra Pak 類飲料盒
    "Plastic bag - wrapper":3,   # 塑膠袋
    "Other plastic":        3,   # 塑膠袋（其他塑膠）
    "Broken glass":         5,   # 一般垃圾
    "Cigarette":            5,   # 一般垃圾
    "Other litter":         5,   # 一般垃圾
    "Styrofoam piece":      5,   # 一般垃圾
    "Unlabeled litter":     5,   # 一般垃圾
    # 略過: "Bottle cap", "Pop tab", "Straw"（無對應類別）
}

CACHE_DIR = Path(ROOT / "data" / "kaggle_cache")


def _force_remove(func, path, _):
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass


def _kaggle_download(dataset_ref: str, dest_zip: Path) -> bool:
    """下載 Kaggle dataset zip，回傳是否成功。"""
    if dest_zip.exists():
        print(f"    [快取] {dest_zip.name} 已存在，跳過下載")
        return True
    dest_zip.parent.mkdir(parents=True, exist_ok=True)
    url = f"https://www.kaggle.com/api/v1/datasets/download/{dataset_ref}"
    print(f"    下載 {dataset_ref} ...")
    try:
        r = requests.get(url, headers=KAGGLE_HEADERS, stream=True, timeout=120)
        r.raise_for_status()
        total = int(r.headers.get("Content-Length", 0))
        wrote = 0
        with open(dest_zip, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                f.write(chunk)
                wrote += len(chunk)
                if total:
                    pct = wrote / total * 100
                    print(f"\r      {pct:.0f}%  ({wrote//1024//1024}MB)", end="", flush=True)
        print()
        return True
    except Exception as e:
        print(f"    [錯誤] Kaggle 下載失敗：{e}")
        if dest_zip.exists():
            dest_zip.unlink()
        return False


def _load_taco_yolo(zip_path: Path, tmp_dir: Path) -> list[dict]:
    """解壓 TACO YOLO zip，讀取標注，回傳樣本列表。"""
    if not zip_path.exists():
        return []
    # 若已解壓且有內容則跳過（OneDrive 上刪除重建會導致暫時無法讀取）
    train_check = tmp_dir / "train" / "images"
    if train_check.exists() and len(list(train_check.glob("*.jpg"))) > 100:
        print(f"    [快取] TACO 已解壓（{len(list(train_check.glob('*.jpg')))} imgs），跳過")
    else:
        print(f"    解壓 {zip_path.name} ...")
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(tmp_dir)

    # 找 data.yaml 取得 TACO 類別名稱列表
    yaml_files = list(tmp_dir.rglob("data.yaml"))
    taco_names: dict[int, str] = {}
    if yaml_files:
        import yaml
        with open(yaml_files[0], encoding="utf-8") as f:
            meta = yaml.safe_load(f)
        raw = meta.get("names", [])
        if isinstance(raw, list):
            taco_names = {i: n for i, n in enumerate(raw)}
        elif isinstance(raw, dict):
            taco_names = raw
    print(f"    TACO 類別數：{len(taco_names)}")

    # 建立 TACO id → 本系統 id 的映射（精確名稱查表）
    taco_id_to_cid: dict[int, int] = {}
    for tid, tname in taco_names.items():
        if tname in TACO_NAME_TO_CID:
            taco_id_to_cid[tid] = TACO_NAME_TO_CID[tname]

    used_names = {taco_names[tid]: cid for tid, cid in taco_id_to_cid.items() if tid in taco_names}
    print(f"    TACO 對應類別：{used_names}")

    # 掃描所有 label txt
    img_dirs = [p for p in tmp_dir.rglob("images") if p.is_dir()]
    samples = []
    for img_dir in img_dirs:
        lbl_dir = img_dir.parent / "labels"
        if not lbl_dir.exists():
            continue
        for img_path in img_dir.glob("*.*"):
            if img_path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".bmp"}:
                continue
            lbl_path = lbl_dir / (img_path.stem + ".txt")  # stem + .txt，避免 .with_suffix 截掉 hash
            if not lbl_path.exists():
                continue
            lines_out = []
            for line in lbl_path.read_text(encoding="utf-8").splitlines():
                parts = line.strip().split()
                if len(parts) < 5:
                    continue
                tid = int(parts[0])
                if tid in taco_id_to_cid:
                    cid = taco_id_to_cid[tid]
                    lines_out.append(f"{cid} " + " ".join(parts[1:]))
            if lines_out:
                samples.append({"img_path": img_path, "lines": lines_out})

    print(f"    TACO 有效樣本：{len(samples)}")
    return samples


def _load_oi_class(cid: int, oi_labels: list[str], split: str, n: int, cache: dict) -> list[dict]:
    """從 Open Images V7 下載指定類別。"""
    import fiftyone.zoo as foz
    import cv2

    _OI_LABEL_TO_CID = {label: cid for label in oi_labels}
    samples_out = []
    per_label = max(1, n // len(oi_labels))

    for label in oi_labels:
        key = (label, split, per_label)
        if key in cache:
            dataset = cache[key]
        else:
            dname = f"_v2_{label.replace(' ','_')}_{split}_{per_label}"
            try:
                dataset = foz.load_zoo_dataset(
                    "open-images-v7", split=split,
                    label_types=["detections"], classes=[label],
                    max_samples=per_label, dataset_name=dname, overwrite=False,
                )
                cache[key] = dataset
                print(f"      [{label}] {len(dataset)} 張")
            except Exception as e:
                print(f"      [{label}] 失敗：{e}")
                continue

        for sample in dataset:
            img_path = Path(sample.filepath)
            if not img_path.exists():
                continue
            detections = sample.ground_truth
            if detections is None:
                continue
            if sample.metadata and sample.metadata.width:
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
                x1, y1, bw, bh = det.bounding_box
                cx = max(0.0, min(1.0, x1 + bw / 2))
                cy = max(0.0, min(1.0, y1 + bh / 2))
                bw = max(0.001, min(1.0, bw))
                bh = max(0.001, min(1.0, bh))
                lines.append(f"{_OI_LABEL_TO_CID[det.label]} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}")
            if lines:
                samples_out.append({"img_path": img_path, "lines": lines})

    return samples_out


def _write_samples(samples: list[dict], out_dir: Path, split: str, limit: int) -> int:
    img_dir = out_dir / split / "images"
    lbl_dir = out_dir / split / "labels"
    img_dir.mkdir(parents=True, exist_ok=True)
    lbl_dir.mkdir(parents=True, exist_ok=True)
    written = 0
    for s in samples[:limit]:
        img_path: Path = s["img_path"]
        dst = img_dir / img_path.name
        if dst.exists():
            dst = img_dir / f"_{written}_{img_path.name}"
        try:
            shutil.copy2(img_path, dst)
            (lbl_dir / dst.stem).with_suffix(".txt").write_text(
                "\n".join(s["lines"]) + "\n", encoding="utf-8"
            )
            written += 1
        except Exception:
            pass
    return written


def _print_distribution(out_dir: Path) -> None:
    counts: dict[int, int] = {cid: 0 for cid in WASTE_CLASSES}
    for lbl in out_dir.rglob("labels/**/*.txt"):
        for line in lbl.read_text(encoding="utf-8").splitlines():
            if line.strip():
                cid = int(line.split()[0])
                counts[cid] = counts.get(cid, 0) + 1
    total = sum(counts.values())
    print("\n  類別分布（bbox 數）：")
    for cid, info in sorted(WASTE_CLASSES.items()):
        n = counts.get(cid, 0)
        pct = n / total * 100 if total else 0
        bar = "#" * int(pct / 2)
        warn = " <-- 樣本不足！" if n < 100 else ""
        print(f"  [{cid}] {info['zh']:<5}  {n:>5} ({pct:5.1f}%)  {bar}{warn}")


def _write_data_yaml(out_dir: Path) -> Path:
    nc = len(WASTE_CLASSES)
    names = "\n".join(
        f"  {cid}: {info['en'].replace(' ','_')}"
        for cid, info in sorted(WASTE_CLASSES.items())
    )
    content = (
        f"path: {out_dir.resolve()}\n"
        "train: train/images\n"
        "val:   valid/images\n\n"
        f"nc: {nc}\nnames:\n{names}\n"
    )
    p = out_dir / "data.yaml"
    p.write_text(content, encoding="utf-8")
    return p


def build(out_dir: Path, n_train: int, n_val: int) -> None:
    print("=" * 64)
    print("  垃圾資料集 v2 建置（正確標籤 + 多來源）")
    print(f"  目標：每類 ~{n_train} train / ~{n_val} val")
    print(f"  輸出：{out_dir.resolve()}")
    print("=" * 64)

    # 清空舊資料集
    if out_dir.exists():
        print(f"\n清除舊資料集：{out_dir}")
        shutil.rmtree(out_dir, onerror=_force_remove)

    t0 = time.time()
    oi_cache: dict = {}

    # ── 1. 下載 Kaggle 資料集 ────────────────────────────────────────────
    print("\n[1/3] Kaggle 資料集下載")
    taco_zip    = CACHE_DIR / "taco_yolo.zip"
    taco_tmp    = CACHE_DIR / "taco_tmp"
    _kaggle_download("vencerlanz09/taco-dataset-yolo-format", taco_zip)

    # ── 2. 解析 TACO ──────────────────────────────────────────────────────
    print("\n[2/3] 解析 TACO YOLO 資料集")
    taco_samples = _load_taco_yolo(taco_zip, taco_tmp)

    # 依 class_id 分組 — 每張圖加入「所有含有的類別」群組
    from collections import defaultdict
    import random
    taco_by_cls: dict[int, list] = defaultdict(list)
    for s in taco_samples:
        seen_cids = set(int(line.split()[0]) for line in s["lines"])
        for cid in seen_cids:
            taco_by_cls[cid].append(s)

    print("  TACO 各類樣本：", {cid: len(v) for cid, v in taco_by_cls.items()})

    # ── 3. Open Images V7（修正標籤） ─────────────────────────────────────
    print("\n[3/3] Open Images V7 下載（修正標籤，不含 Juice）")

    for split, n_target, out_split in [
        ("train", n_train, "train"), ("validation", n_val, "valid")
    ]:
        print(f"\n  {split.upper()} ────────────────────────────────")

        # a. OI 資料
        for cid, oi_labels in OI_CLASS_MAP.items():
            info = WASTE_CLASSES[cid]
            print(f"  OI [{cid}] {info['zh']} ← {oi_labels}")
            samples = _load_oi_class(cid, oi_labels, split, n_target, oi_cache)
            written = _write_samples(samples, out_dir, out_split, n_target)
            print(f"    -> {written} 張")

        # b. TACO 資料（補充所有類別，class 4 鋁箔包靠 TACO）
        for cid in sorted(WASTE_CLASSES.keys()):
            if cid not in taco_by_cls:
                continue
            cls_samples = taco_by_cls[cid][:]
            random.shuffle(cls_samples)
            # train: 全部；val: 20%
            if split == "train":
                batch = cls_samples[:n_target]
            else:
                batch = cls_samples[:max(10, n_target // 4)]
            written = _write_samples(batch, out_dir, out_split, len(batch))
            info = WASTE_CLASSES[cid]
            print(f"  TACO [{cid}] {info['zh']} -> {written} 張")

    # 清理 fiftyone 暫存
    try:
        import fiftyone as fo
        for ds in list(fo.list_datasets()):
            if ds.startswith("_v2_"):
                fo.delete_dataset(ds, verbose=False)
    except Exception:
        pass

    yaml_path = _write_data_yaml(out_dir)
    elapsed = time.time() - t0

    n_tr = len(list((out_dir / "train" / "images").glob("*"))) if (out_dir/"train"/"images").exists() else 0
    n_va = len(list((out_dir / "valid" / "images").glob("*"))) if (out_dir/"valid"/"images").exists() else 0

    print("\n" + "=" * 64)
    print(f"  [OK] 資料集建置完成  ({elapsed/60:.1f} min)")
    print(f"  Train : {n_tr} 張")
    print(f"  Val   : {n_va} 張")
    print(f"  YAML  : {yaml_path}")
    _print_distribution(out_dir)
    print("\n  下一步：python train.py --data dataset/data.yaml --model s --imgsz 640")
    print("=" * 64)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", type=int, default=700)
    parser.add_argument("--val",   type=int, default=175)
    parser.add_argument("--out",   default="dataset")
    args = parser.parse_args()
    build(Path(args.out), args.train, args.val)


if __name__ == "__main__":
    main()
