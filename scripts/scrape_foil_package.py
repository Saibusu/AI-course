"""
scripts/scrape_foil_package.py
從 Bing/Google 搜尋爬取「鋁箔包/利樂包/Tetra Pak/Juice Box」圖片
並自動轉成 YOLO 格式（class 4，全圖 bbox）

使用方式：
  python scripts/scrape_foil_package.py
  python scripts/scrape_foil_package.py --n 500
"""
import argparse, shutil, sys, os
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

QUERIES = [
    # 英文 — 精確的 Tetra Pak 圖片
    "tetra pak juice box packaging",
    "beverage carton drink box",
    "juice box carton aseptic packaging",
    "milk carton tetra pak brick",
    # 中文 — 台灣常見鋁箔包
    "鋁箔包 飲料",
    "利樂包 果汁",
    "光泉 鋁箔包",
    "統一 鋁箔包 包裝",
    # 垃圾桶旁 / 壓扁的（接近實際辨識場景）
    "empty juice carton trash",
    "crushed tetra pak recycling",
    "drink carton waste recycling",
]

CLASS_ID = 4   # 鋁箔包


def scrape(out_dir: Path, n_per_query: int) -> int:
    try:
        from icrawler.builtin import BingImageCrawler, GoogleImageCrawler
    except ImportError:
        sys.exit("請先安裝：pip install icrawler")

    tmp = out_dir / "_raw"
    tmp.mkdir(parents=True, exist_ok=True)
    total = 0

    for i, query in enumerate(QUERIES):
        q_dir = tmp / f"q{i:02d}"
        q_dir.mkdir(exist_ok=True)
        print(f"  [{i+1}/{len(QUERIES)}] Bing: {query}")
        try:
            crawler = BingImageCrawler(
                storage={"root_dir": str(q_dir)},
                feeder_threads=2, parser_threads=2, downloader_threads=4,
            )
            crawler.crawl(keyword=query, max_num=n_per_query,
                          filters={"type": "photo", "size": "medium"})
        except Exception as e:
            print(f"    Bing 失敗：{e}，改用 Google...")
            try:
                crawler = GoogleImageCrawler(storage={"root_dir": str(q_dir)})
                crawler.crawl(keyword=query, max_num=n_per_query)
            except Exception as e2:
                print(f"    Google 也失敗：{e2}，跳過")
                continue

        downloaded = list(q_dir.glob("*.*"))
        total += len(downloaded)
        print(f"    → {len(downloaded)} 張")

    return total


def convert_to_yolo(raw_dir: Path, out_dir: Path, class_id: int) -> int:
    """
    把爬下來的圖片轉成 YOLO 格式（全圖 bbox = 0.5 0.5 1.0 1.0）
    80% train / 20% val 分割
    """
    import random, hashlib
    try:
        from PIL import Image
    except ImportError:
        sys.exit("請先安裝：pip install Pillow")

    all_imgs = [
        p for p in raw_dir.rglob("*")
        if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    ]
    random.shuffle(all_imgs)

    # 去除重複（用 md5）
    seen: set = set()
    unique = []
    for p in all_imgs:
        try:
            h = hashlib.md5(p.read_bytes()).hexdigest()
            if h not in seen:
                seen.add(h)
                unique.append(p)
        except Exception:
            continue

    print(f"\n  原始：{len(all_imgs)} 張，去重後：{len(unique)} 張")

    split_idx = int(len(unique) * 0.8)
    splits = [("train", unique[:split_idx]), ("valid", unique[split_idx:])]

    written = 0
    for split_name, imgs in splits:
        img_dir = out_dir / split_name / "images"
        lbl_dir = out_dir / split_name / "labels"
        img_dir.mkdir(parents=True, exist_ok=True)
        lbl_dir.mkdir(parents=True, exist_ok=True)

        for src in imgs:
            # 驗證圖片可讀
            try:
                with Image.open(src) as im:
                    im.verify()
            except Exception:
                continue

            # 轉成 jpg
            dst_img = img_dir / f"foil_{written:05d}.jpg"
            try:
                with Image.open(src) as im:
                    im.convert("RGB").save(dst_img, "JPEG", quality=90)
            except Exception:
                continue

            # 全圖 bbox
            (lbl_dir / f"foil_{written:05d}.txt").write_text(
                f"{class_id} 0.500000 0.500000 1.000000 1.000000\n", encoding="utf-8"
            )
            written += 1

    return written


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n",   type=int, default=60,  help="每個搜尋詞下載張數（預設 60）")
    parser.add_argument("--out", default="dataset",      help="輸出目錄（預設 dataset/）")
    parser.add_argument("--convert-only", action="store_true",
                        help="跳過下載，只轉換已有圖片")
    args = parser.parse_args()

    out_dir = Path(args.out)
    raw_dir = out_dir / "_raw"

    print("=" * 60)
    print("  鋁箔包圖片爬取 + YOLO 轉換")
    print(f"  搜尋詞：{len(QUERIES)} 個，每詞 {args.n} 張")
    print("=" * 60)

    if not args.convert_only:
        total_raw = scrape(raw_dir, args.n)
        print(f"\n  爬取完成，共 {total_raw} 張原始圖片")
    else:
        print("  跳過爬取，使用已有圖片")

    print("\n  轉換為 YOLO 格式...")
    written = convert_to_yolo(raw_dir, out_dir, CLASS_ID)

    print(f"\n  [OK] 轉換完成：{written} 張有效圖片加入 dataset/")
    print(f"  train: {len(list((out_dir/'train'/'images').glob('foil_*')))} 張")
    print(f"  valid: {len(list((out_dir/'valid'/'images').glob('foil_*')))} 張")
    print(f"\n  完成後執行：python train.py --data dataset/data.yaml --model s --imgsz 640")


if __name__ == "__main__":
    main()
