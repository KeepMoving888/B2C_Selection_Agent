#!/usr/bin/env python3
"""
deploy/generate_load_time_report.py
===================================
根据实测的模型加载时间生成对比图和报告。

实测数据：
  - WSL ext4 (/home/b2cuser/models): 32.10 s
  - E: drive (/mnt/e/models): ~140 s
"""

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUTPUT_DIR = Path("output/model_load_benchmark")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

RESULTS = [
    {"label": "WSL ext4 (/home/b2cuser/models)", "model_path": "/home/b2cuser/models/qwen2.5-7b-ecommerce-awq-v3", "load_time_s": 32.10},
    {"label": "E: drive (/mnt/e/models)", "model_path": "/mnt/e/models/qwen2.5-7b-ecommerce-awq-v3", "load_time_s": 140.0},
]


def main():
    with open(OUTPUT_DIR / "load_time_results.json", "w", encoding="utf-8") as f:
        json.dump(RESULTS, f, ensure_ascii=False, indent=2)

    labels = [r["label"] for r in RESULTS]
    times = [r["load_time_s"] for r in RESULTS]
    slowdown = times[1] / times[0] if times[0] > 0 else 0

    plt.figure(figsize=(8, 5))
    bars = plt.bar(labels, times, color=["#16a34a", "#ef4444"])
    for bar, val in zip(bars, times):
        plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                f"{val:.1f}s", ha="center", va="bottom", fontsize=12)
    plt.ylabel("Model Load Time (s)", fontsize=12)
    plt.title("vLLM AWQ Model Load Time: E: drive vs WSL ext4", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "01_load_time_comparison.png", dpi=150)
    plt.close()

    readme = f"""# vLLM AWQ Model Load Time Benchmark

## Measured Results

| Storage Location | Load Time |
|------------------|-----------|
| WSL ext4 (`/home/b2cuser/models`) | {times[0]:.2f} s |
| E: drive (`/mnt/e/models`) | {times[1]:.2f} s |

**E: drive is {slowdown:.1f}x slower** than WSL ext4 for model loading.

## Why?

WSL2 accesses Windows drives (`/mnt/e`, `/mnt/c`, etc.) via the 9P network protocol, not native block IO.
Even on a fast SSD, 9P adds protocol overhead and does not provide the same sequential-read throughput as
WSL's own ext4 virtual disk. For multi-GB safetensors files, this results in significantly longer load times.

## Recommendation

For production serving, keep the active model on WSL ext4 (`/home/b2cuser/models`) and use E: drive only
for backups or archives. If you must use E: drive, expect ~2-3 minute cold-start load times for a 5GB AWQ model
(and proportionally longer for a 14GB FP16 model).
"""
    with open(OUTPUT_DIR / "README.md", "w", encoding="utf-8") as f:
        f.write(readme)

    print(f"[Load] WSL ext4: {times[0]:.2f}s, E: drive: {times[1]:.2f}s, slowdown: {slowdown:.1f}x")


if __name__ == "__main__":
    main()
