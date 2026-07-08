#!/usr/bin/env python3
"""
deploy/benchmark_vllm_wsl.py
============================
在 WSL2 中启动的 vLLM 服务上进行真实选品请求压测。

测试维度：
  - 单请求延迟（5 次重复）
  - 并发吞吐（1/2/4/8/12/16）
  - 多 batch 吞吐（1/2/4/8/16）
  - 最大可支撑并行量（逐步加压直到失败或超时）

输出：
  - output/vllm_wsl_benchmark/benchmark_results.json
  - output/vllm_wsl_benchmark/*.png
"""

import json
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import requests

BASE_URL = "http://127.0.0.1:8002"
OUTPUT_DIR = Path("output/vllm_wsl_benchmark")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

REAL_PROMPTS = [
    "分析跨境电商平台 dog chew toys 类目的市场机会、竞品卖点与主要风险。",
    "对比 yoga mat 在亚马逊美国站的价格带、评论痛点与供应链集中度。",
    "评估 portable blender 在 TikTok Shop 的爆款潜力，给出定价与卖点建议。",
    "分析 cat water fountain 的季节性趋势、退货原因与头部供应商分布。",
    "请为 camping tent 制定选品决策：是否值得入场？目标利润率与风险点是什么？",
]


def send_request(prompt: str, max_tokens: int = 256) -> dict:
    start = time.time()
    try:
        resp = requests.post(
            f"{BASE_URL}/v1/chat/completions",
            json={
                "model": "/home/b2cuser/models/qwen2.5-7b-ecommerce-awq-v3",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": 0.7,
                "top_p": 0.9,
            },
            timeout=300,
            proxies={"http": None, "https": None},
        )
        latency = time.time() - start
        data = resp.json()
        if resp.status_code == 200:
            choice = data.get("choices", [{}])[0]
            content = choice.get("message", {}).get("content", "")
            usage = data.get("usage", {})
            completion_tokens = usage.get("completion_tokens", 0)
            return {
                "status": "success",
                "latency_s": round(latency, 3),
                "completion_tokens": completion_tokens,
                "tokens_per_sec": round(completion_tokens / latency, 1) if latency > 0 else 0,
                "content_preview": content[:80],
            }
        else:
            return {"status": "error", "latency_s": round(latency, 3), "error": data}
    except Exception as e:
        return {"status": "error", "latency_s": round(time.time() - start, 3), "error": str(e)}


def wait_for_server(timeout: int = 60):
    print("[Bench] Waiting for vLLM server ...", flush=True)
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(f"{BASE_URL}/v1/models", timeout=5, proxies={"http": None, "https": None})
            if r.status_code == 200:
                print("[Bench] Server ready.", flush=True)
                return
        except Exception:
            pass
        time.sleep(1)
    raise RuntimeError("Server not ready")


def run_single_latency_test(repeats: int = 5) -> dict:
    print(f"\n[Bench] Single request latency test: {repeats} repeats", flush=True)
    latencies = []
    tokens_per_sec = []
    for i in range(repeats):
        r = send_request(REAL_PROMPTS[i % len(REAL_PROMPTS)], 256)
        print(f"  Repeat {i+1}: {r['status']}, latency={r['latency_s']}s, tokens/s={r.get('tokens_per_sec')}", flush=True)
        if r["status"] == "success":
            latencies.append(r["latency_s"])
            tokens_per_sec.append(r["tokens_per_sec"])
    return {
        "avg_latency_s": round(statistics.mean(latencies), 3) if latencies else None,
        "min_latency_s": round(min(latencies), 3) if latencies else None,
        "max_latency_s": round(max(latencies), 3) if latencies else None,
        "avg_tokens_per_sec": round(statistics.mean(tokens_per_sec), 1) if tokens_per_sec else None,
    }


def run_concurrency_test(concurrency_levels: list = [1, 2, 4, 8, 12, 16]) -> list:
    print(f"\n[Bench] Concurrency throughput test: {concurrency_levels}", flush=True)
    results = []
    for conc in concurrency_levels:
        print(f"\n  Concurrency={conc}", flush=True)
        prompts = [REAL_PROMPTS[i % len(REAL_PROMPTS)] for i in range(conc * 2)]
        start = time.time()
        responses = []
        with ThreadPoolExecutor(max_workers=conc) as executor:
            futures = [executor.submit(send_request, p, 256) for p in prompts]
            for fut in as_completed(futures):
                responses.append(fut.result())
        total_time = time.time() - start

        success = [r for r in responses if r["status"] == "success"]
        success_rate = len(success) / len(responses) if responses else 0
        latencies = [r["latency_s"] for r in success]
        total_output_tokens = sum(r["completion_tokens"] for r in success)

        result = {
            "concurrency": conc,
            "total_requests": len(prompts),
            "success_count": len(success),
            "success_rate": round(success_rate * 100, 1),
            "total_time_s": round(total_time, 3),
            "throughput_req_per_s": round(len(success) / total_time, 2) if total_time > 0 else 0,
            "throughput_tokens_per_s": round(total_output_tokens / total_time, 1) if total_time > 0 else 0,
            "avg_latency_s": round(statistics.mean(latencies), 3) if latencies else None,
            "p50_latency_s": round(statistics.median(latencies), 3) if latencies else None,
            "p95_latency_s": round(sorted(latencies)[int(len(latencies) * 0.95)] if len(latencies) > 1 else latencies[0], 3) if latencies else None,
        }
        results.append(result)
        print(f"    success={result['success_count']}/{result['total_requests']}, "
              f"success_rate={result['success_rate']}%, "
              f"throughput={result['throughput_req_per_s']} req/s, "
              f"avg_latency={result['avg_latency_s']}s", flush=True)
        # 如果成功率低于 80%，停止继续加压
        if success_rate < 0.8:
            print(f"    [STOP] success rate below 80% at concurrency={conc}", flush=True)
            break
    return results


def run_batch_throughput_test(batch_sizes: list = [1, 2, 4, 8, 16]) -> list:
    print(f"\n[Bench] Multi-batch throughput test: {batch_sizes}", flush=True)
    results = []
    for batch_size in batch_sizes:
        print(f"\n  Batch size={batch_size}", flush=True)
        prompts = [REAL_PROMPTS[i % len(REAL_PROMPTS)] for i in range(batch_size)]
        start = time.time()
        responses = []
        with ThreadPoolExecutor(max_workers=batch_size) as executor:
            futures = [executor.submit(send_request, p, 256) for p in prompts]
            for fut in as_completed(futures):
                responses.append(fut.result())
        total_time = time.time() - start

        success = [r for r in responses if r["status"] == "success"]
        success_rate = len(success) / len(responses) if responses else 0
        latencies = [r["latency_s"] for r in success]
        total_output_tokens = sum(r["completion_tokens"] for r in success)

        single_avg_lat = statistics.mean(latencies) if latencies else 0
        baseline_single = results[0]["avg_latency_s"] if results else single_avg_lat
        ideal_vs_single = baseline_single * batch_size
        speedup_vs_baseline_single = round(ideal_vs_single / total_time, 2) if total_time > 0 else 0.0
        contention_factor = round(single_avg_lat / baseline_single, 2) if baseline_single > 0 else 1.0

        result = {
            "batch_size": batch_size,
            "total_requests": len(prompts),
            "success_count": len(success),
            "success_rate": round(success_rate * 100, 1),
            "total_time_s": round(total_time, 3),
            "throughput_req_per_s": round(len(success) / total_time, 2) if total_time > 0 else 0,
            "throughput_tokens_per_s": round(total_output_tokens / total_time, 1) if total_time > 0 else 0,
            "avg_latency_s": round(single_avg_lat, 3) if latencies else None,
            "p50_latency_s": round(statistics.median(latencies), 3) if latencies else None,
            "p95_latency_s": round(sorted(latencies)[int(len(latencies) * 0.95)] if len(latencies) > 1 else latencies[0], 3) if latencies else None,
            "speedup_vs_baseline_single": speedup_vs_baseline_single,
            "contention_factor": contention_factor,
        }
        results.append(result)
        print(f"    success={result['success_count']}/{result['total_requests']}, "
              f"success_rate={result['success_rate']}%, "
              f"throughput={result['throughput_req_per_s']} req/s, "
              f"avg_latency={result['avg_latency_s']}s, "
              f"speedup_vs_baseline_single={speedup_vs_baseline_single}x", flush=True)
        if success_rate < 0.8:
            print(f"    [STOP] success rate below 80% at batch_size={batch_size}", flush=True)
            break
    return results


def run_max_concurrency_test() -> dict:
    """逐步加压，找到 vLLM 在 current config 下的最大稳定并发量。"""
    print("\n[Bench] Max concurrency stress test", flush=True)
    for conc in [8, 12, 16, 24, 32, 48, 64]:
        print(f"\n  Stress concurrency={conc}", flush=True)
        prompts = [REAL_PROMPTS[i % len(REAL_PROMPTS)] for i in range(conc)]
        start = time.time()
        responses = []
        with ThreadPoolExecutor(max_workers=conc) as executor:
            futures = [executor.submit(send_request, p, 256) for p in prompts]
            for fut in as_completed(futures):
                responses.append(fut.result())
        total_time = time.time() - start
        success = [r for r in responses if r["status"] == "success"]
        success_rate = len(success) / len(responses) if responses else 0
        print(f"    success={len(success)}/{len(prompts)}, rate={success_rate*100:.1f}%, time={total_time:.2f}s", flush=True)
        if success_rate < 0.95:
            return {
                "max_stable_concurrency": conc - 8 if conc > 8 else 0,
                "failure_concurrency": conc,
                "failure_success_rate": round(success_rate * 100, 1),
            }
    return {
        "max_stable_concurrency": 64,
        "failure_concurrency": None,
        "failure_success_rate": None,
    }


def save_charts(single: dict, concurrency: list, batch: list):
    concs = [r["concurrency"] for r in concurrency]
    throughputs = [r["throughput_req_per_s"] for r in concurrency]
    avg_lats = [r["avg_latency_s"] for r in concurrency]
    token_throughputs = [r["throughput_tokens_per_s"] for r in concurrency]

    # 1. 并发 vs 请求吞吐
    plt.figure(figsize=(8, 5))
    plt.plot(concs, throughputs, marker="o", linewidth=2, color="#3b82f6")
    for x, y in zip(concs, throughputs):
        plt.text(x, y, f"{y:.2f}", ha="center", va="bottom", fontsize=10)
    plt.xlabel("Concurrency", fontsize=12)
    plt.ylabel("Throughput (req/s)", fontsize=12)
    plt.title("vLLM WSL Concurrency Throughput", fontsize=14, fontweight="bold")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "01_concurrency_throughput.png", dpi=150)
    plt.close()

    # 2. 并发 vs 平均延迟
    plt.figure(figsize=(8, 5))
    plt.plot(concs, avg_lats, marker="s", linewidth=2, color="#ef4444")
    for x, y in zip(concs, avg_lats):
        plt.text(x, y, f"{y:.2f}s", ha="center", va="bottom", fontsize=10)
    plt.xlabel("Concurrency", fontsize=12)
    plt.ylabel("Avg Latency (s)", fontsize=12)
    plt.title("vLLM WSL Avg Latency by Concurrency", fontsize=14, fontweight="bold")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "02_concurrency_latency.png", dpi=150)
    plt.close()

    # 3. 并发 vs token 吞吐
    plt.figure(figsize=(8, 5))
    plt.bar(concs, token_throughputs, color="#16a34a")
    for x, y in zip(concs, token_throughputs):
        plt.text(x, y, f"{y:.1f}", ha="center", va="bottom", fontsize=10)
    plt.xlabel("Concurrency", fontsize=12)
    plt.ylabel("Token Throughput (tokens/s)", fontsize=12)
    plt.title("vLLM WSL Token Throughput", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "03_concurrency_token_throughput.png", dpi=150)
    plt.close()

    # 4. 单请求延迟
    fig, ax = plt.subplots(figsize=(6, 4))
    metrics = ["avg_latency_s", "min_latency_s", "max_latency_s"]
    labels = ["avg", "min", "max"]
    values = [single.get(m, 0) for m in metrics]
    bars = ax.bar(labels, values, color=["#3b82f6", "#22c55e", "#f97316"])
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                f"{val:.3f}s", ha="center", va="bottom", fontsize=11)
    ax.set_ylabel("Latency (s)", fontsize=12)
    ax.set_title(f"Single Request Latency (tokens/s={single.get('avg_tokens_per_sec', 0):.1f})", fontsize=13, fontweight="bold")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "04_single_request_latency.png", dpi=150)
    plt.close()

    # 5. batch 吞吐 vs 延迟
    if batch:
        batch_sizes = [r["batch_size"] for r in batch]
        batch_throughputs = [r["throughput_req_per_s"] for r in batch]
        batch_avg_lats = [r["avg_latency_s"] for r in batch]

        fig, ax1 = plt.subplots(figsize=(8, 5))
        color = "#3b82f6"
        ax1.set_xlabel("Batch Size", fontsize=12)
        ax1.set_ylabel("Throughput (req/s)", color=color, fontsize=12)
        ax1.plot(batch_sizes, batch_throughputs, marker="o", linewidth=2, color=color)
        for x, y in zip(batch_sizes, batch_throughputs):
            ax1.text(x, y, f"{y:.2f}", ha="center", va="bottom", fontsize=10, color=color)
        ax1.tick_params(axis="y", labelcolor=color)

        ax2 = ax1.twinx()
        color = "#ef4444"
        ax2.set_ylabel("Avg Latency (s)", color=color, fontsize=12)
        ax2.plot(batch_sizes, batch_avg_lats, marker="s", linewidth=2, color=color, linestyle="--")
        for x, y in zip(batch_sizes, batch_avg_lats):
            ax2.text(x, y, f"{y:.2f}s", ha="center", va="top", fontsize=10, color=color)
        ax2.tick_params(axis="y", labelcolor=color)

        plt.title("vLLM WSL Multi-Batch Throughput vs Latency", fontsize=14, fontweight="bold")
        fig.tight_layout()
        plt.savefig(OUTPUT_DIR / "05_batch_throughput_latency.png", dpi=150)
        plt.close()

    # 6. batch speedup vs baseline single
    if batch:
        batch_sizes = [r["batch_size"] for r in batch]
        speedups = [r["speedup_vs_baseline_single"] for r in batch]
        contentions = [r["contention_factor"] for r in batch]

        fig, ax1 = plt.subplots(figsize=(8, 5))
        color = "#8b5cf6"
        ax1.set_xlabel("Batch Size", fontsize=12)
        ax1.set_ylabel("Speedup vs Baseline Single", color=color, fontsize=12)
        bars = ax1.bar(batch_sizes, speedups, color=color, alpha=0.8)
        for bar, val in zip(bars, speedups):
            ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                    f"{val:.2f}x", ha="center", va="bottom", fontsize=10)
        ax1.axhline(1.0, color="gray", linestyle="--", alpha=0.5, label="break-even")
        ax1.tick_params(axis="y", labelcolor=color)
        ax1.set_ylim(0, max(speedups + [1.2]))

        ax2 = ax1.twinx()
        color = "#f59e0b"
        ax2.set_ylabel("Latency Contention Factor", color=color, fontsize=12)
        ax2.plot(batch_sizes, contentions, marker="o", linewidth=2, color=color)
        for x, y in zip(batch_sizes, contentions):
            ax2.text(x, y, f"{y:.1f}x", ha="center", va="bottom", fontsize=10, color=color)
        ax2.tick_params(axis="y", labelcolor=color)

        plt.title("vLLM WSL Batch Speedup & Contention", fontsize=14, fontweight="bold")
        fig.tight_layout()
        plt.savefig(OUTPUT_DIR / "06_batch_speedup.png", dpi=150)
        plt.close()


def main():
    wait_for_server()
    single_result = run_single_latency_test(repeats=5)
    concurrency_results = run_concurrency_test(concurrency_levels=[1, 2, 4, 8, 12, 16])
    batch_results = run_batch_throughput_test(batch_sizes=[1, 2, 4, 8, 16])
    max_concurrency_result = run_max_concurrency_test()

    results = {
        "test_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "server": BASE_URL,
        "single_request": single_result,
        "concurrency": concurrency_results,
        "batch": batch_results,
        "max_concurrency": max_concurrency_result,
    }
    results_path = OUTPUT_DIR / "benchmark_results.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n[Bench] Results saved: {results_path}", flush=True)

    save_charts(single_result, concurrency_results, batch_results)
    print(f"[Bench] Charts saved to: {OUTPUT_DIR}", flush=True)


if __name__ == "__main__":
    main()
