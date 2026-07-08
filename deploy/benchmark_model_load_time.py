#!/usr/bin/env python3
"""
deploy/benchmark_model_load_time.py
====================================
对比 vLLM 从 E 盘（NTFS / WSL 9p）与 WSL ext4 加载 AWQ 模型的时间。

测试方法：
  - 启动 vLLM API server
  - 记录从进程启动到 /v1/models 可访问的时间
  - 分别测试 /mnt/e/models/... 与 /home/b2cuser/models/...

输出：
  - output/model_load_benchmark/load_time_results.json
  - output/model_load_benchmark/01_load_time_comparison.png
  - output/model_load_benchmark/README.md
"""

import json
import subprocess
import sys
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import requests

OUTPUT_DIR = Path("output/model_load_benchmark")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MODEL_PATH_E = "/mnt/e/models/qwen2.5-7b-ecommerce-awq-v3"
MODEL_PATH_EXT4 = "/home/b2cuser/models/qwen2.5-7b-ecommerce-awq-v3"
PORT = 8002


def wait_for_server(port: int, timeout: int = 600) -> float:
    url = f"http://127.0.0.1:{port}/v1/models"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(url, timeout=2)
            if r.status_code == 200:
                return time.time()
        except Exception:
            pass
        time.sleep(0.5)
    raise RuntimeError(f"Server on port {port} not ready within {timeout}s")


def kill_vllm():
    subprocess.run(["pkill", "-f", f"vllm.*{PORT}"], capture_output=True)
    time.sleep(2)


def measure_load_time(model_path: str, label: str) -> dict:
    kill_vllm()
    print(f"\n[Load] Testing {label}: {model_path}", flush=True)
    start = time.time()
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m", "vllm.entrypoints.openai.api_server",
            "--model", model_path,
            "--quantization", "awq",
            "--max-model-len", "4096",
            "--gpu-memory-utilization", "0.85",
            "--max-num-seqs", "8",
            "--port", str(PORT),
            "--host", "0.0.0.0",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        ready_at = wait_for_server(PORT, timeout=600)
        load_time = ready_at - start
        print(f"[Load] {label}: {load_time:.2f}s", flush=True)
        return {"label": label, "model_path": model_path, "load_time_s": round(load_time, 2)}
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except Exception:
            proc.kill()
        kill_vllm()


def save_chart(results: list):
    labels = [r["label"] for r in results]
    times = [r["load_time_s"] for r in results]

    plt.figure(figsize=(7, 5))
    bars = plt.bar(labels, times, color=["#ef4444", "#16a34a"])
    for bar, val in zip(bars, times):
        plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                f"{val:.1f}s", ha="center", va="bottom", fontsize=12)
    plt.ylabel("Model Load Time (s)", fontsize=12)
    plt.title("vLLM AWQ Model Load Time: E: drive vs WSL ext4", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "01_load_time_comparison.png", dpi=150)
    plt.close()


def main():
    results = []
    results.append(measure_load_time(MODEL_PATH_EXT4, "WSL ext4 (/home/b2cuser/models)"))
    results.append(measure_load_time(MODEL_PATH_E, "E: drive (/mnt/e/models)"))

    with open(OUTPUT_DIR / "load_time_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    save_chart(results)

    # README
    ext4_time = results[0]["load_time_s"]
    e_time = results[1]["load_time_s"]
    slowdown = e_time / ext4_time if ext4_time > 0 else 0
    readme = f"""# vLLM AWQ Model Load Time Benchmark

## Results

| Storage Location | Load Time |
|------------------|-----------|
| WSL ext4 (`/home/b2cuser/models`) | {ext4_time:.2f} s |
| E: drive (`/mnt/e/models`) | {e_time:.2f} s |

**E: drive is {slowdown:.1f}x slower** than WSL ext4 for model loading.

## Why?

WSL2 accesses Windows drives (`/mnt/e`, etc.) via the 9P network protocol, not native block IO.
For large sequential reads (multi-GB safetensors), throughput is significantly lower than WSL's
own ext4 virtual disk, even when the underlying disk is a fast SSD.

## Recommendation

For production serving, keep the active model on WSL ext4 (`/home/b2cuser/models`) and use
E: drive only for backups or archives.
"""
    with open(OUTPUT_DIR / "README.md", "w", encoding="utf-8") as f:
        f.write(readme)

    print(f"\n[Load] E: drive load time: {e_time:.2f}s, WSL ext4 load time: {ext4_time:.2f}s, slowdown: {slowdown:.1f}x")


if __name__ == "__main__":
    main()
