#!/usr/bin/env python3
# Copyright (c) 2026 李軒杰, 黃義鈞
# Datung University — I4210 AI實務專題
"""
Parse tegrastats log into structured CSV for performance analysis.

Usage:
    # Capture: tegrastats --interval 1000 --logfile tegrastats.log (run for ≥60s)
    python scripts/parse_tegrastats.py tegrastats.log utilization.csv

Output CSV columns:
    t, cpu_avg_pct, gpu_pct, ram_used_mb, vdd_in_mw, vdd_cpu_mw,
    vdd_gpu_mw, vdd_soc_mw, gpu_temp_c, cpu_temp_c
"""

import re
import csv
import sys
from pathlib import Path


# tegrastats line example (Jetson Orin Nano JetPack 6.x):
# 06-08-2026 14:23:01 RAM 1234/7765MB (lfb 512x4MB) SWAP 0/3882MB ...
# CPU [12%@1190,15%@1190,10%@1190,11%@1190] EMC_FREQ 0% GR3D_FREQ 45%
# VDD_IN 5000mW VDD_CPU_CV 1200mW VDD_SOC 800mW
# CPU@45.0C gpu@52.0C

_PATTERNS = {
    "ram_used_mb": re.compile(r"RAM (\d+)/\d+MB"),
    "gpu_pct":     re.compile(r"GR3D_FREQ (\d+)%"),
    "vdd_in_mw":   re.compile(r"VDD_IN (\d+)mW"),
    "vdd_cpu_mw":  re.compile(r"VDD_CPU_CV (\d+)mW"),
    "vdd_gpu_mw":  re.compile(r"VDD_GPU_CV (\d+)mW"),
    "vdd_soc_mw":  re.compile(r"VDD_SOC (\d+)mW"),
    "gpu_temp_c":  re.compile(r"GPU@([\d.]+)C"),
    "cpu_temp_c":  re.compile(r"CPU@([\d.]+)C"),
    "cpu_cores":   re.compile(r"CPU \[([^\]]+)\]"),
    "timestamp":   re.compile(r"^(\d{2}-\d{2}-\d{4} \d{2}:\d{2}:\d{2})"),
}

_CPU_CORE_PCT = re.compile(r"(\d+)%@\d+")


def parse_cpu_avg(cpu_str: str) -> float:
    pcts = _CPU_CORE_PCT.findall(cpu_str)
    if not pcts:
        return 0.0
    return sum(int(p) for p in pcts) / len(pcts)


def parse_line(line: str) -> dict | None:
    row: dict = {}

    ts_m = _PATTERNS["timestamp"].search(line)
    row["t"] = ts_m.group(1) if ts_m else ""

    for key, pat in _PATTERNS.items():
        if key in ("timestamp", "cpu_cores"):
            continue
        m = pat.search(line)
        row[key] = float(m.group(1)) if m else None

    cpu_m = _PATTERNS["cpu_cores"].search(line)
    row["cpu_avg_pct"] = parse_cpu_avg(cpu_m.group(1)) if cpu_m else None

    if row["gpu_pct"] is None and row["ram_used_mb"] is None:
        return None
    return row


COLUMNS = [
    "t", "cpu_avg_pct", "gpu_pct", "ram_used_mb",
    "vdd_in_mw", "vdd_cpu_mw", "vdd_gpu_mw", "vdd_soc_mw",
    "gpu_temp_c", "cpu_temp_c",
]


def main(log_path: str, out_path: str) -> None:
    rows = []
    with open(log_path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            row = parse_line(line.strip())
            if row:
                rows.append(row)

    if not rows:
        print("No valid tegrastats entries found.", file=sys.stderr)
        sys.exit(1)

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    print(f"Parsed {len(rows)} samples → {out_path}")

    # Summary stats
    gpu_vals = [r["gpu_pct"] for r in rows if r["gpu_pct"] is not None]
    cpu_vals = [r["cpu_avg_pct"] for r in rows if r["cpu_avg_pct"] is not None]
    vdd_vals = [r["vdd_in_mw"] for r in rows if r["vdd_in_mw"] is not None]

    if gpu_vals:
        print(f"GPU utilization: avg={sum(gpu_vals)/len(gpu_vals):.1f}% "
              f"max={max(gpu_vals):.1f}%")
    if cpu_vals:
        print(f"CPU utilization: avg={sum(cpu_vals)/len(cpu_vals):.1f}% "
              f"max={max(cpu_vals):.1f}%")
    if vdd_vals:
        print(f"Power (VDD_IN): avg={sum(vdd_vals)/len(vdd_vals):.0f}mW "
              f"max={max(vdd_vals):.0f}mW")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
