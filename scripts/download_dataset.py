"""
scripts/download_dataset.py — 下載 Roboflow 廢棄物資料集並重新映射為 6 類
智慧零接觸垃圾分類系統

建議資料集（擇一，依涵蓋率排序）：
  1. TACO Trash Annotations in Context（推薦）
       --workspace msed --project taco-trash-annotations-in-context --version 18
       ~1,500 張，含塑膠袋、鋁箔包、瓶罐、紙箱等完整 6 類覆蓋

  2. Garbage Detection（備選）
       --workspace grpan --project garbage-classification-3 --version 1
       ~2,000 張，以瓶罐、紙類為主，鋁箔包較少

  3. 自訂 Roboflow 專案
       --workspace YOUR_WS --project YOUR_PROJECT --version 1

使用方式：
  # 取得 API Key：https://roboflow.com → Settings → Roboflow API
  python scripts/download_dataset.py --key YOUR_API_KEY

  # 指定資料集（TACO）
  python scripts/download_dataset.py --key YOUR_KEY \\
      --workspace msed --project taco-trash-annotations-in-context --version 18
"""

import argparse
import logging
import os
import shutil
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# 預設資料集（TACO）
WORKSPACE = "msed"
PROJECT   = "taco-trash-annotations-in-context"
VERSION   = 18

# ── 6 類映射：原始類別名稱（小寫）→ 本系統類別 ID ──────────────────────────
#
#   0: PET_Bottle       (寶特瓶  → 綠燈)
#   1: Aluminum_Can     (鐵鋁罐  → 黃燈)
#   2: Paper_Container  (紙餐盒  → 藍燈)
#   3: Plastic_Bag      (塑膠袋  → 白燈)
#   4: Foil_Package     (鋁箔包  → 橘燈)
#   5: General_Waste    (一般垃圾 → 紅燈)
#
# 命名慣例：TACO category → 本系統 ID
# 若原始資料集類別不在此表，預設 fallback → General_Waste (5)
CLASS_REMAP: dict[str, int] = {
    # ── 寶特瓶 (0) ──────────────────────────────────────────────────
    "bottle":                       0,
    "plastic bottle":               0,
    "plastic-bottle":               0,
    "pet bottle":                   0,
    "pet_bottle":                   0,
    "beverage bottle":              0,
    "water bottle":                 0,
    "plastic cup":                  0,
    "plastic container":            0,
    "clear plastic bottle":         0,
    "other plastic bottle":         0,
    "disposable plastic cup":       0,
    "single-use plastic cup":       0,
    "cup":                          0,

    # ── 鐵鋁罐 (1) ──────────────────────────────────────────────────
    "can":                          1,
    "aluminum can":                 1,
    "aluminium can":                1,
    "aluminum-can":                 1,
    "metal can":                    1,
    "tin":                          1,
    "tin can":                      1,
    "aerosol":                      1,
    "aerosols":                     1,
    "scrap metal":                  1,
    "metal":                        1,
    "drink can":                    1,
    "beverage can":                 1,

    # ── 紙餐盒 (2) ──────────────────────────────────────────────────
    "paper":                        2,
    "cardboard":                    2,
    "carton":                       2,
    "paper box":                    2,
    "paper-box":                    2,
    "box":                          2,
    "paper bag":                    2,
    "paper-bag":                    2,
    "paper cup":                    2,
    "newspaper":                    2,
    "magazine paper":               2,
    "corrugated carton":            2,
    "egg carton":                   2,
    "pizza box":                    2,
    "meal carton":                  2,
    "paper packaging":              2,

    # ── 塑膠袋 (3) ──────────────────────────────────────────────────
    "plastic bag":                  3,
    "plastic-bag":                  3,
    "plastic bag wrapper":          3,
    "plastic bags & wrapper":       3,
    "plastic film":                 3,
    "plastic wrap":                 3,
    "plastic wrapping":             3,
    "wrapper":                      3,
    "cling wrap":                   3,
    "garbage bag":                  3,
    "carrier bag":                  3,
    "shopping bag":                 3,
    "six pack rings":               3,
    "plastic straw":                3,
    "straw":                        3,
    "plastic utensils":             3,
    "plastic gloves":               3,

    # ── 鋁箔包 (4) ──────────────────────────────────────────────────
    "aluminium foil":               4,
    "aluminum foil":                4,
    "foil":                         4,
    "juice box":                    4,
    "juice carton":                 4,
    "drink carton":                 4,
    "beverage carton":              4,
    "tetra pak":                    4,
    "tetrapak":                     4,
    "milk carton":                  4,
    "food carton":                  4,
    "foil food container":          4,
    "crisp packet":                 4,
    "chips bag":                    4,
    "snack bag":                    4,
    "sweet wrapper":                4,
    "candy wrapper":                4,

    # ── 一般垃圾 (5) ─────────────────────────────────────────────────
    "glass":                        5,
    "glass bottle":                 5,
    "broken glass":                 5,
    "cigarette":                    5,
    "cigarette butt":               5,
    "food waste":                   5,
    "organic":                      5,
    "other":                        5,
    "trash":                        5,
    "garbage":                      5,
    "general":                      5,
    "wood":                         5,
    "rope":                         5,
    "battery":                      5,
    "styrofoam piece":              5,
    "foam cup":                     5,
    "blister pack":                 5,
    "lid":                          5,
    "bottle cap":                   5,
    "unlabeled litter":             5,
}


def _build_new_names() -> dict[int, str]:
    """從 config.WASTE_CLASSES 取得英文名稱（與訓練保持同步）。"""
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from config import WASTE_CLASSES
    return {cid: info["en"].replace(" ", "_") for cid, info in WASTE_CLASSES.items()}


def _build_data_yaml(out_dir: Path) -> str:
    """動態從 config.WASTE_CLASSES 生成 data.yaml 內容。"""
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
        "# data.yaml — 廢棄物分類資料集（由 download_dataset.py 自動產生）\n"
        f"path: {out_dir.resolve()}\n"
        "train: train/images\n"
        "val:   valid/images\n"
        "test:  test/images\n\n"
        f"nc: {nc}\n"
        f"names:\n{names_lines}\n"
    )


def _download(api_key: str, dst_root: Path) -> Path:
    try:
        from roboflow import Roboflow
    except ImportError:
        raise SystemExit(
            "請先安裝 roboflow 套件：\n"
            "  pip install roboflow\n"
            "或：pip install -r requirements.dev.txt"
        )

    logger.info(f"連線 Roboflow… workspace={WORKSPACE}, project={PROJECT}, v{VERSION}")
    rf      = Roboflow(api_key=api_key)
    project = rf.workspace(WORKSPACE).project(PROJECT)
    dataset = project.version(VERSION).download("yolov8", location=str(dst_root / "_raw"))
    raw_dir = Path(dataset.location)
    logger.info(f"下載完成：{raw_dir}")
    return raw_dir


def _read_class_names(data_yaml: Path) -> list[str]:
    import yaml
    with open(data_yaml, encoding="utf-8") as f:
        meta = yaml.safe_load(f)
    names = meta.get("names", {})
    if isinstance(names, dict):
        return [names[i] for i in sorted(names.keys())]
    return list(names)


def _build_id_map(original_names: list[str], new_names: dict[int, str]) -> dict[int, int]:
    """
    建立 原始 class_id → 新 class_id 的映射表。
    無法映射的類別 fallback → General_Waste (最後一個 class_id)。
    """
    fallback_id = max(new_names.keys())
    id_map: dict[int, int] = {}
    for old_id, name in enumerate(original_names):
        key = name.lower().strip()
        new_id = CLASS_REMAP.get(key)
        if new_id is None:
            # 部分比對（類別名稱含有關鍵字）
            for kw, mapped_id in CLASS_REMAP.items():
                if kw in key or key in kw:
                    new_id = mapped_id
                    break
        if new_id is None:
            new_id = fallback_id
            logger.warning(f"  '{name}' 無映射規則 → {new_names[fallback_id]}")
        else:
            logger.info(f"  '{name}' → {new_names[new_id]}")
        id_map[old_id] = new_id
    return id_map


def _remap_labels(src_dir: Path, dst_dir: Path, id_map: dict[int, int]) -> int:
    label_files = list(src_dir.glob("**/*.txt"))
    count = 0
    for src_lbl in label_files:
        rel     = src_lbl.relative_to(src_dir)
        dst_lbl = dst_dir / rel
        dst_lbl.parent.mkdir(parents=True, exist_ok=True)

        lines_out = []
        for line in src_lbl.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            parts  = line.split()
            old_id = int(parts[0])
            new_id = id_map.get(old_id, max(id_map.values()))
            lines_out.append(f"{new_id} {' '.join(parts[1:])}")
        dst_lbl.write_text("\n".join(lines_out) + "\n", encoding="utf-8")
        count += 1
    return count


def _copy_images(src_dir: Path, dst_dir: Path) -> int:
    img_exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    img_files = [f for f in src_dir.glob("**/*") if f.suffix.lower() in img_exts]
    for src_img in img_files:
        rel     = src_img.relative_to(src_dir)
        dst_img = dst_dir / rel
        dst_img.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_img, dst_img)
    return len(img_files)


def _log_class_distribution(out_dir: Path, new_names: dict[int, str]) -> None:
    """統計每個類別的標注數量，方便確認資料是否平衡。"""
    counts = {cid: 0 for cid in new_names}
    for lbl in out_dir.rglob("labels/**/*.txt"):
        for line in lbl.read_text(encoding="utf-8").splitlines():
            if line.strip():
                cid = int(line.split()[0])
                counts[cid] = counts.get(cid, 0) + 1
    logger.info("\n類別分布（bbox 數量）：")
    total = sum(counts.values())
    for cid, name in sorted(new_names.items()):
        n   = counts.get(cid, 0)
        pct = n / total * 100 if total else 0
        bar = "█" * int(pct / 2)
        logger.info(f"  [{cid}] {name:<22} {n:>5} ({pct:5.1f}%)  {bar}")


def prepare_dataset(raw_dir: Path, out_dir: Path) -> None:
    new_names = _build_new_names()

    raw_yaml = raw_dir / "data.yaml"
    if not raw_yaml.exists():
        candidates = list(raw_dir.rglob("data.yaml"))
        if not candidates:
            raise FileNotFoundError(f"找不到 data.yaml：{raw_dir}")
        raw_yaml = candidates[0]

    original_names = _read_class_names(raw_yaml)
    logger.info(f"\n原始類別（共 {len(original_names)} 類）：{original_names}")
    logger.info(f"映射至本系統 {len(new_names)} 類：")
    id_map = _build_id_map(original_names, new_names)

    splits    = ["train", "valid", "test"]
    total_img = total_lbl = 0
    for split in splits:
        src_img_dir = raw_yaml.parent / split / "images"
        src_lbl_dir = raw_yaml.parent / split / "labels"
        if not src_img_dir.exists():
            continue
        dst_img_dir = out_dir / split / "images"
        dst_lbl_dir = out_dir / split / "labels"
        n_img = _copy_images(src_img_dir, dst_img_dir)
        n_lbl = _remap_labels(src_lbl_dir, dst_lbl_dir, id_map) if src_lbl_dir.exists() else 0
        logger.info(f"  {split}: {n_img} 張圖片, {n_lbl} 份標註")
        total_img += n_img
        total_lbl += n_lbl

    data_yaml = out_dir / "data.yaml"
    data_yaml.write_text(_build_data_yaml(out_dir), encoding="utf-8")

    _log_class_distribution(out_dir, new_names)

    logger.info(
        f"\n{'='*55}\n"
        f"  ✅ 資料集準備完成！\n"
        f"  目錄    ：{out_dir}\n"
        f"  總圖片  ：{total_img} 張\n"
        f"  標註數  ：{total_lbl} 份\n"
        f"  data.yaml：{data_yaml}\n\n"
        f"  現在可以開始訓練：\n"
        f"    python train.py\n"
        f"{'='*55}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="下載 Roboflow 廢棄物資料集並重新映射為 6 類",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "建議資料集：\n"
            "  TACO（推薦）：--workspace msed "
            "--project taco-trash-annotations-in-context --version 18\n"
        ),
    )
    parser.add_argument("--key",       default="",        help="Roboflow Private API Key（或設 ROBOFLOW_API_KEY 環境變數）")
    parser.add_argument("--out",       default="dataset", help="輸出目錄（預設：dataset/）")
    parser.add_argument("--workspace", default=WORKSPACE, help=f"Roboflow workspace（預設：{WORKSPACE}）")
    parser.add_argument("--project",   default=PROJECT,   help=f"Roboflow project（預設：{PROJECT}）")
    parser.add_argument("--version",   type=int, default=VERSION, help=f"資料集版本（預設：{VERSION}）")
    args = parser.parse_args()

    api_key = args.key or os.getenv("ROBOFLOW_API_KEY", "")
    if not api_key:
        raise SystemExit(
            "請提供 Roboflow API Key：\n"
            "  --key YOUR_KEY\n"
            "  或設環境變數：ROBOFLOW_API_KEY=YOUR_KEY"
        )

    out_dir = Path(args.out)
    if out_dir.exists():
        logger.warning(f"目錄 {out_dir} 已存在，將覆蓋內容。")

    global WORKSPACE, PROJECT, VERSION
    WORKSPACE = args.workspace
    PROJECT   = args.project
    VERSION   = args.version

    raw_dir = _download(api_key, out_dir.parent / "dataset_tmp")
    prepare_dataset(raw_dir, out_dir)

    tmp = out_dir.parent / "dataset_tmp"
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
