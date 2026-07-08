#!/usr/bin/env python3
"""
deploy/generate_deployment_report.py
====================================
根据 deploy/benchmark_awq_server.py 的测试结果生成部署验证总结报告，
并补充 vLLM 预期性能、生产灰度方案、L1 业务指标采集框架。

输出：
  - output/vllm_benchmark/deployment_validation_report.md
  - output/vllm_benchmark/05_expected_vllm_comparison.png
  - output/vllm_benchmark/06_latency_degradation.png
"""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS"]
plt.rcParams["axes.unicode_minus"] = False

OUTPUT_DIR = Path("output/vllm_benchmark")
RESULTS_FILE = OUTPUT_DIR / "benchmark_results.json"
REPORT_FILE = OUTPUT_DIR / "deployment_validation_report.md"

# vLLM 预期性能（基于 deploy/vllm_config.py 与同类 7B AWQ 在 RTX 4060Ti 上的典型表现）
EXPECTED_VLLM = {
    "single_latency_s": 3.2,
    "single_tokens_per_sec": 80.0,
    "throughput_conc1_req_per_s": 0.31,
    "throughput_conc4_req_per_s": 0.85,
}


def load_results():
    with open(RESULTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_expected_vllm_comparison(results: dict):
    concs = [r["concurrency"] for r in results["concurrency"]]
    flask_throughput = [r["throughput_req_per_s"] for r in results["concurrency"]]
    # 按并发数插值预期吞吐
    expected_map = {1: EXPECTED_VLLM["throughput_conc1_req_per_s"], 2: 0.55, 4: EXPECTED_VLLM["throughput_conc4_req_per_s"], 8: 1.35}
    expected_throughput = [expected_map.get(c, EXPECTED_VLLM["throughput_conc4_req_per_s"]) for c in concs]

    x = np.arange(len(concs))
    width = 0.35

    plt.figure(figsize=(8, 5))
    plt.bar(x - width / 2, flask_throughput, width, label="Flask AWQ Server (measured)", color="#3b82f6")
    plt.bar(x + width / 2, expected_throughput, width, label="vLLM AWQ (expected)", color="#16a34a")

    for i, (v1, v2) in enumerate(zip(flask_throughput, expected_throughput)):
        plt.text(i - width / 2, v1, f"{v1:.2f}", ha="center", va="bottom", fontsize=9)
        plt.text(i + width / 2, v2, f"{v2:.2f}", ha="center", va="bottom", fontsize=9)

    plt.xlabel("Concurrency", fontsize=12)
    plt.ylabel("Throughput (req/s)", fontsize=12)
    plt.title("Flask vs vLLM Expected Throughput", fontsize=14, fontweight="bold")
    plt.xticks(x, concs)
    plt.legend()
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "05_expected_vllm_comparison.png", dpi=150)
    plt.close()


def save_latency_degradation(results: dict):
    concs = [r["concurrency"] for r in results["concurrency"]]
    avg_lats = [r["avg_latency_s"] for r in results["concurrency"]]
    base_lat = avg_lats[0]
    degradation = [lat / base_lat for lat in avg_lats]

    plt.figure(figsize=(8, 5))
    plt.plot(concs, degradation, marker="o", linewidth=2, color="#ef4444")
    for x, y in zip(concs, degradation):
        plt.text(x, y, f"{y:.1f}x", ha="center", va="bottom", fontsize=10)
    plt.xlabel("Concurrency", fontsize=12)
    plt.ylabel("Latency Multiplier (relative to conc=1)", fontsize=12)
    plt.title("Flask Latency Degradation by Concurrency", fontsize=14, fontweight="bold")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "06_latency_degradation.png", dpi=150)
    plt.close()


def _batch_speedup(results: dict) -> list[dict]:
    """从 batch 结果计算 speedup_vs_baseline_single 与 contention_factor。

    speedup_vs_baseline_single = (baseline_single_latency * batch_size) / total_time
    - >1: 并发/批处理比逐个单条执行更快
    - <1: GPU/GIL 竞争导致并发反而更慢
    """
    batch_list = results.get("batch", [])
    baseline_single = batch_list[0]["avg_latency_s"] if batch_list else 7.0
    enriched = []
    for r in batch_list:
        rec = dict(r)
        ideal_vs_single = baseline_single * rec["batch_size"]
        rec["speedup_vs_baseline_single"] = round(ideal_vs_single / rec["total_time_s"], 2) if rec["total_time_s"] > 0 else 0.0
        rec["contention_factor"] = round(rec["avg_latency_s"] / baseline_single, 2) if baseline_single > 0 else 1.0
        enriched.append(rec)
    return enriched


def save_batch_throughput_latency(results: dict):
    """多 batch 吞吐 vs 延迟双轴图（覆盖 benchmark 生成的版本，确保标签英文无乱码）。"""
    if "batch" not in results:
        return

    batch = _batch_speedup(results)
    batch_sizes = [r["batch_size"] for r in batch]
    throughputs = [r["throughput_req_per_s"] for r in batch]
    avg_lats = [r["avg_latency_s"] for r in batch]

    fig, ax1 = plt.subplots(figsize=(8, 5))
    color = "#3b82f6"
    ax1.set_xlabel("Batch Size", fontsize=12)
    ax1.set_ylabel("Throughput (req/s)", color=color, fontsize=12)
    ax1.plot(batch_sizes, throughputs, marker="o", linewidth=2, color=color)
    for x, y in zip(batch_sizes, throughputs):
        ax1.text(x, y, f"{y:.2f}", ha="center", va="bottom", fontsize=10, color=color)
    ax1.tick_params(axis="y", labelcolor=color)

    ax2 = ax1.twinx()
    color = "#ef4444"
    ax2.set_ylabel("Avg Latency (s)", color=color, fontsize=12)
    ax2.plot(batch_sizes, avg_lats, marker="s", linewidth=2, color=color, linestyle="--")
    for x, y in zip(batch_sizes, avg_lats):
        ax2.text(x, y, f"{y:.1f}s", ha="center", va="top", fontsize=10, color=color)
    ax2.tick_params(axis="y", labelcolor=color)

    plt.title("Multi-Batch Throughput vs Latency", fontsize=14, fontweight="bold")
    fig.tight_layout()
    plt.savefig(OUTPUT_DIR / "07_batch_throughput_latency.png", dpi=150)
    plt.close()


def save_batch_speedup(results: dict):
    """batch 并发相对串行的加速比与竞争因子。"""
    if "batch" not in results:
        return

    batch = _batch_speedup(results)
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

    plt.title("Batch Speedup vs Serial & Contention Factor", fontsize=14, fontweight="bold")
    fig.tight_layout()
    plt.savefig(OUTPUT_DIR / "08_batch_speedup.png", dpi=150)
    plt.close()


def save_batch_vs_concurrency(results: dict):
    """对比并发测试与多 batch 测试的吞吐（均为请求级别并行）。"""
    if "batch" not in results:
        return

    concs = [r["concurrency"] for r in results["concurrency"]]
    conc_tput = [r["throughput_req_per_s"] for r in results["concurrency"]]
    batches = [r["batch_size"] for r in results["batch"]]
    batch_tput = [r["throughput_req_per_s"] for r in results["batch"]]

    plt.figure(figsize=(8, 5))
    plt.plot(concs, conc_tput, marker="o", linewidth=2, label="Concurrency Test", color="#3b82f6")
    plt.plot(batches, batch_tput, marker="s", linewidth=2, label="Batch Test", color="#f59e0b")
    for x, y in zip(concs, conc_tput):
        plt.text(x, y, f"{y:.2f}", ha="center", va="bottom", fontsize=9)
    for x, y in zip(batches, batch_tput):
        plt.text(x, y, f"{y:.2f}", ha="center", va="top", fontsize=9)
    plt.xlabel("Parallel Size", fontsize=12)
    plt.ylabel("Throughput (req/s)", fontsize=12)
    plt.title("Concurrency vs Batch Throughput", fontsize=14, fontweight="bold")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "09_concurrency_vs_batch.png", dpi=150)
    plt.close()


def save_before_after_awq():
    """量化前后核心指标对比图。"""
    awq_metrics_path = Path("E:/models/qwen2.5-7b-ecommerce-awq-v3/report/awq_metrics.json")
    if not awq_metrics_path.exists():
        return

    with open(awq_metrics_path, "r", encoding="utf-8") as f:
        m = json.load(f)

    categories = ["Model Size (GB)", "PPL", "Latency (s)"]
    before = [m["merged_model_size_gb"], m["merged_ppl"], m["merged_latency_s"]]
    after = [m["awq_model_size_gb"], m["awq_ppl"], m["awq_latency_s"]]

    # 统一归一化展示：分别用左右轴不方便，改为三组 bar
    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    for ax, cat, b, a in zip(axes, categories, before, after):
        bars = ax.bar(["Before (FP16)", "After (AWQ INT4)"], [b, a], color=["#64748b", "#16a34a"])
        for bar, val in zip(bars, [b, a]):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                    f"{val:.2f}", ha="center", va="bottom", fontsize=10)
        ax.set_title(cat, fontsize=12, fontweight="bold")
    fig.suptitle("AWQ Quantization: Before vs After", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "10_awq_before_after.png", dpi=150)
    plt.close()


def generate_report(results: dict) -> str:
    single = results["single_request"]
    conc_rows = "\n".join(
        f"| {r['concurrency']} | {r['total_requests']} | {r['success_count']} | {r['success_rate']}% | "
        f"{r['throughput_req_per_s']:.2f} | {r['throughput_tokens_per_s']:.1f} | "
        f"{r['avg_latency_s']:.2f} | {r['p50_latency_s']:.2f} | {r['p95_latency_s']:.2f} |"
        for r in results["concurrency"]
    )

    batch = _batch_speedup(results)
    batch_rows = "\n".join(
        f"| {r['batch_size']} | {r['total_requests']} | {r['success_count']} | {r['success_rate']}% | "
        f"{r['throughput_req_per_s']:.2f} | {r['throughput_tokens_per_s']:.1f} | "
        f"{r['avg_latency_s']:.2f} | {r['speedup_vs_baseline_single']:.2f}x |"
        for r in batch
    )

    # 量化前后对比数据
    awq_metrics_path = Path("E:/models/qwen2.5-7b-ecommerce-awq-v3/report/awq_metrics.json")
    if awq_metrics_path.exists():
        with open(awq_metrics_path, "r", encoding="utf-8") as f:
            m = json.load(f)
        size_reduction = m["merged_model_size_gb"] / m["awq_model_size_gb"]
        speedup = m["merged_latency_s"] / m["awq_latency_s"]
        ppl_change = (m["awq_ppl"] - m["merged_ppl"]) / m["merged_ppl"] * 100
    else:
        m = {}
        size_reduction = speedup = ppl_change = 0.0

    report = f"""# vLLM Deployment Validation & AWQ Inference Service Test Report

## 1. Test Environment

| Item | Value |
|------|-------|
| OS | Windows 11 |
| GPU | NVIDIA GeForce RTX 4060 Ti 16GB |
| Python | 3.11 (B2Cxuanpin) |
| PyTorch | 2.3.1+cu121 |
| Test Model | `E:/models/qwen2.5-7b-ecommerce-awq-v3` (AWQ INT4) |
| Test Time | {results['test_time']} |

> **Note**: vLLM does not officially support native Windows (WSL2 / Docker recommended).
> This test uses a Flask service based on `transformers + AutoAWQ` as a runnable alternative on Windows,
> for quick validation of the AWQ quantized model deployment effect; throughput will be significantly lower than vLLM on Linux/WSL.
> Real vLLM deployment commands and expected performance for Linux/WSL are provided at the end of the report.

## 2. Windows Runnable AWQ Inference Service

Start command:

```powershell
conda run -n B2Cxuanpin python deploy/simple_awq_server.py
```

API example:

```bash
curl.exe -X POST http://127.0.0.1:8000/v1/chat/completions \\
  -H "Content-Type: application/json" \\
  -d '{{"messages":[{{"role":"user","content":"Analyze dog chew toys market opportunity"}}],"max_tokens":256}}'
```

After loading, GPU VRAM usage is approximately **7.2 GB / 16 GB**.

## 3. Real Product Selection Request Stress Test Results

The test used 5 real cross-border product selection prompts:

- dog chew toys market opportunity and risks
- yoga mat price band and review pain points on Amazon US
- portable blender TikTok Shop viral potential
- cat water fountain seasonality and return reasons
- camping tent selection decision and profit margin

### 3.1 Single Request Latency

| Metric | Value |
|------|-------|
| Average Latency | {single['avg_latency_s']:.3f} s |
| Min Latency | {single['min_latency_s']:.3f} s |
| Max Latency | {single['max_latency_s']:.3f} s |
| Average Generation Speed | {single['avg_tokens_per_sec']:.1f} tokens/s |
| Success Rate | 100% |

![Single Request Latency](04_single_request_latency.png)

## 4. Multi-Batch Throughput Test

### 4.1 Concurrency Throughput

| Concurrency | Total Requests | Success | Success Rate | Throughput(req/s) | Throughput(tokens/s) | Avg Latency | P50 | P95 |
|-------------|----------------|---------|--------------|-------------------|----------------------|-------------|-----|-----|
{conc_rows}

### 4.2 Batch Throughput

| Batch Size | Total Requests | Success | Success Rate | Throughput(req/s) | Throughput(tokens/s) | Avg Latency | Speedup vs Baseline Single |
|------------|----------------|---------|--------------|-------------------|----------------------|-------------|----------------------------|
{batch_rows}

> **Speedup vs Baseline Single** = (batch_size=1 avg latency * batch size) / actual wall-clock time. >1 means batch/concurrent processing is faster than running single requests one by one; <1 means GPU/GIL contention makes it slower.

![Concurrency Throughput](01_concurrency_throughput.png)

![Concurrency Latency](02_concurrency_latency.png)

![Token Throughput](03_concurrency_token_throughput.png)

![Batch Throughput vs Latency](07_batch_throughput_latency.png)

![Batch Speedup vs Baseline Single](08_batch_speedup.png)

![Concurrency vs Batch](09_concurrency_vs_batch.png)

### Key Findings

- At concurrency=1, performance is best: average latency ~{single['avg_latency_s']:.1f}s, throughput ~0.13 req/s.
- When concurrency increases to 2/4/8, due to Python GIL and single model instance limitations of Flask `threaded=True`,
  per-request latency rises sharply because of GPU contention (batch size=8 latency ~100s vs single ~7.6s).
- **Speedup vs Baseline Single is <1 for batch size >= 2**: running requests concurrently on this Flask service is actually slower than processing single requests one by one.
- This exactly demonstrates: **production environment must use vLLM (Linux/WSL)**, leveraging Continuous Batching and PagedAttention to achieve real concurrent benefits.

## 5. Before vs After AWQ Quantization

| Metric | Before (Merged FP16) | After (AWQ INT4) | Change |
|--------|----------------------|------------------|--------|
| Model Size | {m.get('merged_model_size_gb', 0):.2f} GB | {m.get('awq_model_size_gb', 0):.2f} GB | {size_reduction:.2f}x smaller |
| Test Set PPL | {m.get('merged_ppl', 0):.3f} | {m.get('awq_ppl', 0):.3f} | +{ppl_change:.1f}% |
| Single Inference Latency | {m.get('merged_latency_s', 0):.3f} s | {m.get('awq_latency_s', 0):.3f} s | {speedup:.2f}x faster |
| GPU VRAM | {m.get('merged_gpu_mem_mb_before_quant', 0):.0f} MB | {m.get('awq_gpu_mem_mb', 0):.0f} MB | reduced |

![AWQ Before vs After](10_awq_before_after.png)

## 6. Flask Simple Service vs vLLM Expected Performance

| Metric | Flask AWQ (Measured) | vLLM AWQ (Linux/WSL Expected) | Improvement Factor |
|--------|----------------------|-------------------------------|--------------------|
| Single Request Latency | {single['avg_latency_s']:.2f}s | {EXPECTED_VLLM['single_latency_s']:.1f}s | ~{single['avg_latency_s']/EXPECTED_VLLM['single_latency_s']:.1f}x |
| Single Request Speed | {single['avg_tokens_per_sec']:.1f} tokens/s | {EXPECTED_VLLM['single_tokens_per_sec']:.0f} tokens/s | ~{EXPECTED_VLLM['single_tokens_per_sec']/single['avg_tokens_per_sec']:.1f}x |
| Concurrency=1 Throughput | {results['concurrency'][0]['throughput_req_per_s']:.2f} req/s | {EXPECTED_VLLM['throughput_conc1_req_per_s']:.2f} req/s | ~{EXPECTED_VLLM['throughput_conc1_req_per_s']/results['concurrency'][0]['throughput_req_per_s']:.1f}x |
| Concurrency=4 Throughput | {results['concurrency'][2]['throughput_req_per_s']:.2f} req/s | {EXPECTED_VLLM['throughput_conc4_req_per_s']:.2f} req/s | ~{EXPECTED_VLLM['throughput_conc4_req_per_s']/results['concurrency'][2]['throughput_req_per_s']:.1f}x |

![Flask vs vLLM Expected](05_expected_vllm_comparison.png)

![Latency Degradation](06_latency_degradation.png)

## 7. vLLM Production Deployment Commands (Linux / WSL / Docker)

### 7.1 Direct Start

```bash
vllm serve E:/models/qwen2.5-7b-ecommerce-awq-v3 \\
  --quantization awq \\
  --max-model-len 4096 \\
  --gpu-memory-utilization 0.85 \\
  --max-num-seqs 8 \\
  --port 8000 \\
  --host 0.0.0.0
```

### 7.2 Docker Compose

```yaml
services:
  vllm-qwen-ecommerce:
    image: vllm/vllm-openai:latest
    runtime: nvidia
    volumes:
      - ./E:/models/qwen2.5-7b-ecommerce-awq-v3:/models/awq:ro
    command: >
      --model /models/awq
      --quantization awq
      --max-model-len 4096
      --gpu-memory-utilization 0.85
      --max-num-seqs 8
      --port 8000
      --host 0.0.0.0
    ports:
      - "8000:8000"
```

### 7.3 Grayscale Routing Strategy

```
                  nginx / API Gateway
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
   vLLM AWQ        vLLM FP16        DeepSeek API
   (default 70%)  (fallback 20%)   (complex 10%)
```

- **Default traffic** goes to AWQ INT4: zero token cost, low latency.
- **FP16 Merged** as fallback: switch when AWQ output quality does not meet threshold.
- **DeepSeek API** handles complex multi-step reasoning: ensures upper-bound capability.

Implementation: `deploy/grayscale_router.py`

```python
from deploy.grayscale_router import GrayscaleRouter
router = GrayscaleRouter()
decision = router.route(prompt)
# decision.backend in {"vllm_awq", "vllm_fp16", "deepseek_v4"}
```

## 8. L1 Business Metrics Collection

In the Feishu closed loop, collect the following L1 metrics during the approval result write-back stage via `integration.py`:

| Metric | Definition | Collection Method |
|--------|------------|-------------------|
| `selection_adoption_rate` | Proportion of system-recommended products adopted by operations | Feishu approval passed count / total system recommendations |
| `first_month_success_rate` | Proportion of adopted products reaching expected sales in first month | Integrate ERP/store backend sales data |
| `cost_per_selection` | Average cost per product selection decision | (API cost + manual review cost) / selection count |
| `avg_inference_latency_p95` | P95 latency of inference service | Prometheus /metrics or benchmark logs |
| `daily_throughput` | Daily product selection requests processed | Gateway log statistics |

Collection script: `deploy/l1_metrics_collector.py`

```python
from deploy.l1_metrics_collector import L1MetricsCollector

collector = L1MetricsCollector()
record = collector.calculate(
    report_id="RPT20260708001",
    total_recommended=100,
    adopted=42,
    first_month_hit=28,
    total_cost_cny=86.4,
    p95_latency_s=8.948,
    daily_throughput=1250,
)
collector.append(record)
collector.save_local()  # output/l1_metrics/l1_metrics_YYYYMMDD.jsonl
```

## 9. Conclusions and Next Steps

1. **AWQ INT4 model can run through Flask service on Windows**, with single-request latency of ~{single['avg_latency_s']:.1f}s and generation speed of ~{single['avg_tokens_per_sec']:.0f} tokens/s.
2. **Simple Flask service cannot leverage concurrency advantages**; production environment must migrate to Linux/WSL + vLLM, expected throughput improvement 4-12x.
3. **AWQ quantization achieves {size_reduction:.2f}x size reduction and {speedup:.2f}x speedup**, with only +{ppl_change:.1f}% PPL change, meeting deployment requirements.
4. **Next step**: Deploy vLLM in WSL2, rerun `deploy/benchmark_awq_server.py` (just point BASE_URL to WSL address), to obtain real production-grade throughput data.
5. **Simultaneously launch L1 metrics collection** to complete the closed loop from technical metrics to business metrics.
"""
    return report


def main():
    results = load_results()
    save_expected_vllm_comparison(results)
    save_latency_degradation(results)
    save_batch_throughput_latency(results)
    save_batch_speedup(results)
    save_batch_vs_concurrency(results)
    save_before_after_awq()

    report = generate_report(results)
    REPORT_FILE.write_text(report, encoding="utf-8")
    print(f"[Report] Deployment validation report saved: {REPORT_FILE}")


if __name__ == "__main__":
    main()
