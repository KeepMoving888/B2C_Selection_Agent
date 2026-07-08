#!/usr/bin/env python3
"""
deploy/benchmark_awq_server.py
==============================
对 deploy/simple_awq_server.py 进行压测与吞吐测试。

测试维度：
  1. 单请求延迟（TTFT / 总延迟 / tokens/s）
  2. 不同并发下的 throughput（req/s）与平均延迟
  3. 真实选品请求成功率

输出：
  - output/vllm_benchmark/benchmark_results.json
  - output/vllm_benchmark/*.png 对比图

用法：
    # 先启动服务
    python deploy/simple_awq_server.py

    # 再运行压测
    python deploy/benchmark_awq_server.py
"""

import json
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import matplotlib.pyplot as plt
import requests

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS"]
plt.rcParams["axes.unicode_minus"] = False

BASE_URL = "http://127.0.0.1:8000"
CHAT_URL = f"{BASE_URL}/v1/chat/completions"
HEALTH_URL = f"{BASE_URL}/health"

OUTPUT_DIR = Path("output/vllm_benchmark")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# --------------------------- 真实选品 prompt ---------------------------
REAL_PROMPTS = [
    "请分析跨境电商平台 dog chew toys 类目的市场机会、竞品卖点与主要风险。",
    "对比 yoga mat 在亚马逊美国站的价格带、评论痛点与供应链集中度。",
    "评估 portable blender 在 TikTok Shop 的爆款潜力，给出定价与卖点建议。",
    "分析 cat water fountain 的季节性趋势、退货原因与头部供应商分布。",
    "请为 camping tent 制定选品决策：是否值得入场？目标利润率与风险点是什么？",
]


def wait_for_server(timeout: int = 120):
    print("[Bench] Waiting for server ...", flush=True)
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(HEALTH_URL, timeout=2)
            if r.status_code == 200:
                print(f"[Bench] Server ready: {r.json()}", flush=True)
                return True
        except Exception:
            pass
        time.sleep(1)
    raise RuntimeError("Server not available")


def send_request(prompt: str, max_tokens: int = 256) -> dict:
    payload = {
        "model": "awq-qwen2.5-7b-ecommerce",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.7,
        "top_p": 0.9,
    }
    start = time.time()
    try:
        r = requests.post(CHAT_URL, json=payload, timeout=120)
        latency = time.time() - start
        if r.status_code == 200:
            data = r.json()
            return {
                "status": "success",
                "latency_s": latency,
                "prompt_tokens": data["usage"]["prompt_tokens"],
                "completion_tokens": data["usage"]["completion_tokens"],
                "total_tokens": data["usage"]["total_tokens"],
            }
        else:
            return {"status": "error", "latency_s": latency, "error": r.text}
    except Exception as e:
        return {"status": "error", "latency_s": time.time() - start, "error": str(e)}


def run_single_latency_test(repeats: int = 5) -> dict:
    print(f"\n[Bench] Single-request latency test (repeats={repeats})", flush=True)
    latencies = []
    tokens_per_sec = []
    for i in range(repeats):
        res = send_request(REAL_PROMPTS[i % len(REAL_PROMPTS)], max_tokens=256)
        if res["status"] == "success":
            latencies.append(res["latency_s"])
            if res["completion_tokens"] > 0:
                tokens_per_sec.append(res["completion_tokens"] / res["latency_s"])
            print(f"  Run {i+1}: latency={res['latency_s']:.3f}s, "
                  f"output_tokens={res['completion_tokens']}, "
                  f"tokens/s={res['completion_tokens']/res['latency_s']:.1f}", flush=True)
        else:
            print(f"  Run {i+1}: ERROR {res.get('error')}", flush=True)

    return {
        "avg_latency_s": round(statistics.mean(latencies), 3) if latencies else None,
        "min_latency_s": round(min(latencies), 3) if latencies else None,
        "max_latency_s": round(max(latencies), 3) if latencies else None,
        "avg_tokens_per_sec": round(statistics.mean(tokens_per_sec), 1) if tokens_per_sec else None,
    }


def run_concurrency_test(concurrency_levels: list = [1, 2, 4, 8]) -> list:
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
    return results


def save_charts(single: dict, concurrency: list):
    concs = [r["concurrency"] for r in concurrency]
    throughputs = [r["throughput_req_per_s"] for r in concurrency]
    avg_lats = [r["avg_latency_s"] for r in concurrency]
    token_throughputs = [r["throughput_tokens_per_s"] for r in concurrency]

    # 1. 并发 vs 请求吞吐
    plt.figure(figsize=(8, 5))
    plt.plot(concs, throughputs, marker="o", linewidth=2, color="#3b82f6")
    for x, y in zip(concs, throughputs):
        plt.text(x, y, f"{y:.2f}", ha="center", va="bottom", fontsize=10)
    plt.xlabel("并发数", fontsize=12)
    plt.ylabel("Throughput (req/s)", fontsize=12)
    plt.title("AWQ 服务并发请求吞吐", fontsize=14, fontweight="bold")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "01_concurrency_throughput.png", dpi=150)
    plt.close()

    # 2. 并发 vs 平均延迟
    plt.figure(figsize=(8, 5))
    plt.plot(concs, avg_lats, marker="s", linewidth=2, color="#ef4444")
    for x, y in zip(concs, avg_lats):
        plt.text(x, y, f"{y:.2f}s", ha="center", va="bottom", fontsize=10)
    plt.xlabel("并发数", fontsize=12)
    plt.ylabel("平均延迟 (s)", fontsize=12)
    plt.title("AWQ 服务平均延迟随并发变化", fontsize=14, fontweight="bold")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "02_concurrency_latency.png", dpi=150)
    plt.close()

    # 3. 并发 vs token 吞吐
    plt.figure(figsize=(8, 5))
    plt.bar(concs, token_throughputs, color="#16a34a")
    for x, y in zip(concs, token_throughputs):
        plt.text(x, y, f"{y:.1f}", ha="center", va="bottom", fontsize=10)
    plt.xlabel("并发数", fontsize=12)
    plt.ylabel("Token Throughput (tokens/s)", fontsize=12)
    plt.title("AWQ 服务 Token 吞吐", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "03_concurrency_token_throughput.png", dpi=150)
    plt.close()

    # 4. 单请求延迟仪表盘
    fig, ax = plt.subplots(figsize=(6, 4))
    metrics = ["avg_latency_s", "min_latency_s", "max_latency_s"]
    labels = ["平均", "最小", "最大"]
    values = [single.get(m, 0) for m in metrics]
    bars = ax.bar(labels, values, color=["#3b82f6", "#22c55e", "#f97316"])
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                f"{val:.3f}s", ha="center", va="bottom", fontsize=11)
    ax.set_ylabel("延迟 (s)", fontsize=12)
    ax.set_title(f"单请求延迟（tokens/s={single.get('avg_tokens_per_sec', 0):.1f}）", fontsize=13, fontweight="bold")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "04_single_request_latency.png", dpi=150)
    plt.close()


def main():
    wait_for_server()
    single_result = run_single_latency_test(repeats=5)
    concurrency_results = run_concurrency_test(concurrency_levels=[1, 2, 4])

    results = {
        "test_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "server": BASE_URL,
        "single_request": single_result,
        "concurrency": concurrency_results,
    }
    results_path = OUTPUT_DIR / "benchmark_results.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n[Bench] Results saved: {results_path}", flush=True)

    save_charts(single_result, concurrency_results)
    print(f"[Bench] Charts saved to: {OUTPUT_DIR}", flush=True)


if __name__ == "__main__":
    main()
