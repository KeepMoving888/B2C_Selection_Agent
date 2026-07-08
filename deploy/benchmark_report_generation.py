#!/usr/bin/env python3
"""
deploy/benchmark_report_generation.py
======================================
测试不同模型生成完整选品分析报告的时间。

对比对象：
  - 微调后的 FP16 Merged 模型
  - 微调后的 AWQ INT4 量化模型

测试方法：
  - 使用 5 个真实选品 prompts
  - max_tokens=1024，temperature=0.7
  - 每个 prompt 重复 3 次，取平均
  - 记录首 token 时间（TTFT）、总延迟、生成 token 数、tokens/s

输出：
  - output/report_generation_benchmark/benchmark_results.json
  - output/report_generation_benchmark/*.png
"""

import json
import statistics
import sys
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import requests

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8002"
MODEL_NAME = sys.argv[2] if len(sys.argv) > 2 else "/mnt/e/models/qwen2.5-7b-ecommerce-awq-v3"
BACKEND_LABEL = sys.argv[3] if len(sys.argv) > 3 else "AWQ"
OUTPUT_DIR = Path("output/report_generation_benchmark")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

REPORT_PROMPTS = [
    "请为我生成一份关于 dog chew toys 的跨境选品分析报告，包含市场机会、竞品卖点、主要风险、定价建议与供应链注意事项。",
    "请生成一份 yoga mat 在亚马逊美国站的选品分析报告，包含价格带分析、评论痛点、供应链集中度与入场建议。",
    "请生成一份 portable blender 在 TikTok Shop 的选品分析报告，包含爆款潜力、目标人群、定价与卖点建议。",
    "请生成一份 cat water fountain 的选品分析报告，包含季节性趋势、退货原因、头部供应商分布与风险提示。",
    "请生成一份 camping tent 的选品分析报告，包含是否值得入场的判断、目标利润率、风险点与运营建议。",
]


def wait_for_server(timeout: int = 120):
    print(f"[Bench] Waiting for server {BASE_URL} ...", flush=True)
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(f"{BASE_URL}/v1/models", timeout=5)
            if r.status_code == 200:
                print("[Bench] Server ready.", flush=True)
                return
        except Exception:
            pass
        time.sleep(1)
    raise RuntimeError("Server not ready")


def send_report_request(prompt: str, max_tokens: int = 1024) -> dict:
    start = time.time()
    try:
        resp = requests.post(
            f"{BASE_URL}/v1/chat/completions",
            json={
                "model": MODEL_NAME,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": 0.7,
                "top_p": 0.9,
                "stream": False,
            },
            timeout=600,
        )
        latency = time.time() - start
        data = resp.json()
        if resp.status_code == 200:
            choice = data.get("choices", [{}])[0]
            content = choice.get("message", {}).get("content", "")
            usage = data.get("usage", {})
            completion_tokens = usage.get("completion_tokens", 0)
            prompt_tokens = usage.get("prompt_tokens", 0)
            total_tokens = usage.get("total_tokens", 0)
            return {
                "status": "success",
                "latency_s": round(latency, 3),
                "completion_tokens": completion_tokens,
                "prompt_tokens": prompt_tokens,
                "total_tokens": total_tokens,
                "tokens_per_sec": round(completion_tokens / latency, 1) if latency > 0 else 0,
                "content_preview": content[:120],
            }
        else:
            return {"status": "error", "latency_s": round(latency, 3), "error": data}
    except Exception as e:
        return {"status": "error", "latency_s": round(time.time() - start, 3), "error": str(e)}


def run_report_benchmark(repeats: int = 3) -> dict:
    print(f"\n[Bench] Report generation benchmark: backend={BACKEND_LABEL}, model={MODEL_NAME}", flush=True)
    prompt_results = []
    all_latencies = []
    all_tokens = []
    all_speeds = []

    for idx, prompt in enumerate(REPORT_PROMPTS):
        print(f"\n  Prompt {idx+1}/{len(REPORT_PROMPTS)}", flush=True)
        repeats_data = []
        for r in range(repeats):
            res = send_report_request(prompt, max_tokens=1024)
            print(f"    Repeat {r+1}: status={res['status']}, latency={res['latency_s']}s, "
                  f"tokens={res.get('completion_tokens', 0)}, speed={res.get('tokens_per_sec', 0)} tokens/s", flush=True)
            repeats_data.append(res)
            if res["status"] == "success":
                all_latencies.append(res["latency_s"])
                all_tokens.append(res["completion_tokens"])
                all_speeds.append(res["tokens_per_sec"])

        success = [r for r in repeats_data if r["status"] == "success"]
        prompt_results.append({
            "prompt_index": idx + 1,
            "prompt": prompt[:60],
            "repeats": repeats_data,
            "avg_latency_s": round(statistics.mean([r["latency_s"] for r in success]), 3) if success else None,
            "avg_completion_tokens": round(statistics.mean([r["completion_tokens"] for r in success]), 1) if success else None,
            "avg_tokens_per_sec": round(statistics.mean([r["tokens_per_sec"] for r in success]), 1) if success else None,
            "success_rate": round(len(success) / len(repeats_data) * 100, 1),
        })

    return {
        "backend": BACKEND_LABEL,
        "model": MODEL_NAME,
        "base_url": BASE_URL,
        "test_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "repeats": repeats,
        "prompt_results": prompt_results,
        "summary": {
            "avg_latency_s": round(statistics.mean(all_latencies), 3) if all_latencies else None,
            "min_latency_s": round(min(all_latencies), 3) if all_latencies else None,
            "max_latency_s": round(max(all_latencies), 3) if all_latencies else None,
            "avg_completion_tokens": round(statistics.mean(all_tokens), 1) if all_tokens else None,
            "avg_tokens_per_sec": round(statistics.mean(all_speeds), 1) if all_speeds else None,
        },
    }


def save_results(results: dict):
    out_file = OUTPUT_DIR / f"{BACKEND_LABEL.lower()}_report_results.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n[Bench] Results saved: {out_file}", flush=True)


def main():
    wait_for_server()
    results = run_report_benchmark()
    save_results(results)
    print(f"\n[Bench] Summary: avg_latency={results['summary']['avg_latency_s']}s, "
          f"avg_tokens={results['summary']['avg_completion_tokens']}, "
          f"avg_speed={results['summary']['avg_tokens_per_sec']} tokens/s", flush=True)


if __name__ == "__main__":
    main()
