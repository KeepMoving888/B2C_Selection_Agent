#!/usr/bin/env python3
"""
finetune/quantize_awq_with_metrics.py
=====================================
对已经 merge_and_unload 后的 FP16 模型进行 AWQ INT4 量化，
同步记录：模型大小、量化耗时、显存占用、测试集困惑度 (PPL)、
单条推理延迟，并把指标同步到 WandB。

量化结束后自动与 Base 模型、Merged FP16 模型做垂直领域测试集对比，
生成对比图表与 Markdown 总结报告。

用法示例：
    conda run -n B2Cxuanpin python finetune/quantize_awq_with_metrics.py \
        --merged_model models/qwen2.5-7b-ecommerce-merged \
        --output_dir models/qwen2.5-7b-ecommerce-awq \
        --calib_data finetune/data/orpo_train.jsonl \
        --test_data finetune/data/orpo_test.jsonl \
        --max_calib_samples 128 \
        --max_test_samples 100 \
        --wandb_project b2c-product-selection
"""

import argparse
import json
import os
import sys
import time
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import torch
from awq import AutoAWQForCausalLM
from transformers import AutoModelForCausalLM, AutoTokenizer

# 优先从项目根目录 .env 读取 WANDB_API_KEY 等环境变量
PROJECT_ROOT = Path(__file__).resolve().parent.parent
try:
    from dotenv import load_dotenv

    load_dotenv(PROJECT_ROOT / ".env", override=True)
except Exception:
    pass

import wandb  # noqa: E402

warnings.filterwarnings("ignore")

# ------------------------------------------------------------------
# 工具函数
# ------------------------------------------------------------------

def get_dir_size_gb(path: Path) -> float:
    """统计目录下 safetensors/bin 文件总大小（GB）。

    若存在 model.safetensors.index.json / pytorch_model.bin.index.json，
    仅统计索引中引用的文件，避免 merge 后残留的重复单文件导致统计翻倍。
    """
    total = 0
    index_file = path / "model.safetensors.index.json"
    if not index_file.exists():
        index_file = path / "pytorch_model.bin.index.json"

    if index_file.exists():
        with open(index_file, "r", encoding="utf-8") as f:
            index = json.load(f)
        referenced = set(index.get("weight_map", {}).values())
        for fname in referenced:
            fp = path / fname
            if fp.exists():
                total += fp.stat().st_size
        return round(total / (1024**3), 2)

    for p in path.rglob("*"):
        if p.is_file() and p.suffix in {".safetensors", ".bin"}:
            total += p.stat().st_size
    return round(total / (1024**3), 2)


def format_size(path: Path) -> str:
    gb = get_dir_size_gb(path)
    return f"{gb} GB"


def load_calibration_texts(calib_path: str, max_samples: int = 128,
                            tokenizer=None, max_length: int = 256):
    import json as _json

    texts = []
    with open(calib_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            ex = _json.loads(line)
            prompt = ex.get("prompt", "")
            chosen = ex.get("chosen", "")
            text = (
                f"<|im_start|>user\n{prompt}<|im_end|>\n"
                f"<|im_start|>assistant\n{chosen}<|im_end|>"
            )
            # 若提供 tokenizer，按 token 长度截断，降低 AWQ 校准耗时
            if tokenizer is not None and max_length is not None:
                ids = tokenizer(text, truncation=True, max_length=max_length,
                                add_special_tokens=False)["input_ids"]
                text = tokenizer.decode(ids, skip_special_tokens=False)
            texts.append(text)
            if len(texts) >= max_samples:
                break
    return texts


def load_test_texts(test_path: str, max_samples: int = 100):
    import json as _json

    texts = []
    with open(test_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            ex = _json.loads(line)
            prompt = ex.get("prompt", "")
            chosen = ex.get("chosen", "")
            text = (
                f"<|im_start|>user\n{prompt}<|im_end|>\n"
                f"<|im_start|>assistant\n{chosen}<|im_end|>"
            )
            texts.append(text)
            if len(texts) >= max_samples:
                break
    return texts


def compute_ppl(model, tokenizer, texts, max_length: int = 512):
    """计算平均困惑度（PPL）。"""
    model.eval()
    total_nll = 0.0
    total_tokens = 0
    device = next(model.parameters()).device
    for text in texts:
        inputs = tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=max_length,
        )
        inputs = {k: v.to(device) for k, v in inputs.items()}
        with torch.no_grad():
            outputs = model(**inputs, labels=inputs["input_ids"])
        nll = outputs.loss.item() * inputs["input_ids"].size(1)
        total_nll += nll
        total_tokens += inputs["input_ids"].size(1)
    avg_nll = total_nll / total_tokens
    return float(np.exp(avg_nll))


def measure_latency(model, tokenizer, prompt: str, max_new_tokens: int = 128, repeats: int = 3):
    """测量单条生成平均延迟（秒）。"""
    device = next(model.parameters()).device
    inputs = tokenizer(prompt, return_tensors="pt").to(device)
    # warmup
    with torch.no_grad():
        _ = model.generate(**inputs, max_new_tokens=10, do_sample=False)
    torch.cuda.synchronize()
    times = []
    for _ in range(repeats):
        start = time.time()
        with torch.no_grad():
            _ = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False)
        torch.cuda.synchronize()
        times.append(time.time() - start)
    return float(np.mean(times))


def get_gpu_memory_mb():
    return torch.cuda.memory_allocated() / (1024**2)


def save_bar_chart(categories, values, ylabel, title, path: Path, colors=None):
    plt.figure(figsize=(8, 5))
    bars = plt.bar(categories, values, color=colors or ["#2563eb"])
    plt.ylabel(ylabel, fontsize=12)
    plt.title(title, fontsize=14, fontweight="bold")
    for bar, val in zip(bars, values):
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{val:.2f}",
            ha="center",
            va="bottom",
            fontsize=11,
        )
    plt.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(path, dpi=150)
    plt.close()


# ------------------------------------------------------------------
# 主流程
# ------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--merged_model",
        default="models/qwen2.5-7b-ecommerce-merged",
        help="已合并的 FP16 模型目录",
    )
    parser.add_argument(
        "--output_dir",
        default="models/qwen2.5-7b-ecommerce-awq",
        help="AWQ 量化模型保存目录",
    )
    parser.add_argument(
        "--base_model",
        default="models/qwen/Qwen2.5-7B",
        help="原始 Base 模型目录（用于对比评估）",
    )
    parser.add_argument(
        "--calib_data",
        default="finetune/data/orpo_train.jsonl",
        help="AWQ 校准数据",
    )
    parser.add_argument(
        "--test_data",
        default="finetune/data/orpo_test.jsonl",
        help="测试集，用于 PPL / 偏好对评估",
    )
    parser.add_argument("--bits", type=int, default=4)
    parser.add_argument("--group_size", type=int, default=128)
    parser.add_argument(
        "--max_calib_samples",
        type=int,
        default=16,
        help="AWQ 校准样本数量，默认 16，可在速度与精度间平衡",
    )
    parser.add_argument(
        "--max_calib_length",
        type=int,
        default=256,
        help="AWQ 校准文本最大 token 长度，默认 256",
    )
    parser.add_argument("--max_test_samples", type=int, default=100)
    parser.add_argument("--max_ppl_samples", type=int, default=50)
    parser.add_argument(
        "--wandb_project",
        default=os.getenv("WANDB_PROJECT", "b2c-product-selection"),
    )
    parser.add_argument(
        "--wandb_run_name",
        default=os.getenv("WANDB_RUN_NAME", "awq-qwen2.5-7b-ecommerce"),
    )
    parser.add_argument(
        "--skip_quantize",
        action="store_true",
        help="跳过 AWQ 量化，直接加载 output_dir 中的已量化模型进行后续评估",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    merged_path = Path(args.merged_model)
    output_dir = Path(args.output_dir)
    report_dir = output_dir / "report"
    report_dir.mkdir(parents=True, exist_ok=True)

    # ---------- WandB 初始化 ----------
    wandb_enabled = os.getenv("WANDB_API_KEY") is not None
    if wandb_enabled:
        wandb.init(
            project=args.wandb_project,
            name=args.wandb_run_name,
            config=vars(args),
        )
        print(f"[INFO] WandB 已初始化: {args.wandb_project}/{args.wandb_run_name}", flush=True)
    else:
        print("[WARN] 未检测到 WANDB_API_KEY，跳过 WandB 同步。", flush=True)

    metrics = {"args": vars(args)}

    # ---------- 1. 模型大小（不加载） ----------
    merged_size_gb = get_dir_size_gb(merged_path)
    print(f"[INFO] Merged FP16 模型大小: {merged_size_gb} GB", flush=True)
    metrics["merged_model_size_gb"] = merged_size_gb

    # ---------- 2. 加载 Merged 模型并测 PPL / 延迟 ----------
    print("[INFO] 加载 Merged FP16 模型（AutoAWQ 包装器，后续直接量化）...", flush=True)
    tokenizer = AutoTokenizer.from_pretrained(merged_path, trust_remote_code=True)
    merged_model = AutoAWQForCausalLM.from_pretrained(
        merged_path,
        trust_remote_code=True,
        safetensors=True,
        device_map="cuda:0",
    )
    print("[INFO] Merged 模型已加载到 GPU", flush=True)

    test_texts = load_test_texts(args.test_data, args.max_ppl_samples)
    print(f"[INFO] 计算 Merged 模型在 {len(test_texts)} 条测试样本上的 PPL...", flush=True)
    merged_ppl = compute_ppl(merged_model, tokenizer, test_texts)
    print(f"[METRIC] Merged PPL: {merged_ppl:.3f}", flush=True)

    prompt_for_latency = "请分析跨境电商平台 dog chew toys 类目的市场机会与风险。"
    print("[INFO] 测量 Merged 模型推理延迟...", flush=True)
    merged_latency = measure_latency(merged_model, tokenizer, prompt_for_latency)
    print(f"[METRIC] Merged 延迟: {merged_latency:.3f}s", flush=True)

    metrics.update(
        {
            "merged_ppl": merged_ppl,
            "merged_latency_s": merged_latency,
            "merged_gpu_mem_mb_before_quant": get_gpu_memory_mb(),
        }
    )

    # ---------- 3. AWQ 量化 ----------
    if args.skip_quantize:
        print("[INFO] --skip_quantize 已启用，跳过 AWQ 量化...", flush=True)
        calib_texts = []
        quant_time_s = 0.0
        awq_size_gb = get_dir_size_gb(output_dir)
        print(f"[INFO] 已量化模型大小: {awq_size_gb} GB", flush=True)
        metrics.update(
            {
                "quant_time_s": quant_time_s,
                "awq_model_size_gb": awq_size_gb,
                "size_reduction_ratio": round(merged_size_gb / awq_size_gb, 2),
            }
        )
        # 释放 Merged 模型，再加载已保存的 AWQ 模型
        print("[INFO] 释放 Merged FP16 模型...", flush=True)
        del merged_model
        torch.cuda.empty_cache()
        print(f"[INFO] 从 {output_dir} 加载 AWQ INT4 模型...", flush=True)
        awq_model = AutoModelForCausalLM.from_pretrained(
            str(output_dir),
            device_map="auto",
            trust_remote_code=True,
        )
        awq_tokenizer = AutoTokenizer.from_pretrained(str(output_dir), trust_remote_code=True)
        print("[INFO] AWQ 模型已加载", flush=True)
    else:
        print("[INFO] 开始 AWQ 量化...", flush=True)
        calib_texts = load_calibration_texts(
            args.calib_data,
            args.max_calib_samples,
            tokenizer=tokenizer,
            max_length=args.max_calib_length,
        )
        print(
            f"[INFO] 加载 {len(calib_texts)} 条校准样本，每条最大长度 {args.max_calib_length} tokens",
            flush=True,
        )

        quant_config = {
            "zero_point": True,
            "q_group_size": args.group_size,
            "w_bit": args.bits,
        }
        print(f"[INFO] AWQ 配置: {quant_config}", flush=True)

        # AutoAWQ 直接复用已加载的 merged_model 进行量化
        print("[INFO] 正在执行 model.quantize()，第一层初始化可能较慢，请耐心等待...", flush=True)
        start_quant = time.time()
        merged_model.quantize(tokenizer, quant_config=quant_config, calib_data=calib_texts)
        quant_time_s = time.time() - start_quant
        print(f"[METRIC] AWQ 量化耗时: {quant_time_s:.1f}s", flush=True)

        print(f"[INFO] 保存 AWQ 模型到 {output_dir}", flush=True)
        # AutoAWQ 在 Windows 上要求路径为字符串
        merged_model.save_quantized(str(output_dir))
        tokenizer.save_pretrained(str(output_dir))

        awq_size_gb = get_dir_size_gb(output_dir)
        print(f"[METRIC] AWQ 模型大小: {awq_size_gb} GB", flush=True)

        metrics.update(
            {
                "quant_time_s": quant_time_s,
                "awq_model_size_gb": awq_size_gb,
                "size_reduction_ratio": round(merged_size_gb / awq_size_gb, 2),
                "gpu_mem_mb_after_quant": get_gpu_memory_mb(),
            }
        )

        # ---------- 4. 重新加载 AWQ 模型并测 PPL / 延迟 ----------
        # AutoAWQ 量化后内部存在 CPU/GPU 张量混布，直接 forward 会报 device 不一致，
        # 因此保存后重新用 AutoModelForCausalLM + device_map 加载最为稳妥。
        print("[INFO] 释放量化前模型并重新加载 AWQ 量化模型...", flush=True)
        del merged_model
        torch.cuda.empty_cache()

        print(f"[INFO] 从 {output_dir} 加载 AWQ INT4 模型...", flush=True)
        awq_model = AutoModelForCausalLM.from_pretrained(
            str(output_dir),
            device_map="auto",
            trust_remote_code=True,
        )
        awq_tokenizer = AutoTokenizer.from_pretrained(str(output_dir), trust_remote_code=True)
        print("[INFO] AWQ 模型已加载", flush=True)

    print(f"[INFO] 计算 AWQ 模型在 {len(test_texts)} 条测试样本上的 PPL...", flush=True)
    awq_ppl = compute_ppl(awq_model, awq_tokenizer, test_texts)
    print(f"[METRIC] AWQ PPL: {awq_ppl:.3f}", flush=True)

    print("[INFO] 测量 AWQ 模型推理延迟...", flush=True)
    awq_latency = measure_latency(awq_model, awq_tokenizer, prompt_for_latency)
    print(f"[METRIC] AWQ 延迟: {awq_latency:.3f}s", flush=True)

    metrics.update(
        {
            "awq_ppl": awq_ppl,
            "awq_latency_s": awq_latency,
            "awq_gpu_mem_mb": get_gpu_memory_mb(),
        }
    )

    del awq_model
    torch.cuda.empty_cache()

    # ---------- 5. Base 模型对比（可选，若显存允许） ----------
    base_ppl = None
    base_latency = None
    base_path = Path(args.base_model)
    if base_path.exists():
        print("[INFO] 加载 Base 模型做对比...", flush=True)
        try:
            base_model = AutoModelForCausalLM.from_pretrained(
                base_path,
                torch_dtype=torch.float16,
                device_map="cuda:0",
                trust_remote_code=True,
                low_cpu_mem_usage=True,
            )
            base_tokenizer = AutoTokenizer.from_pretrained(base_path, trust_remote_code=True)
            print("[INFO] 计算 Base 模型 PPL...", flush=True)
            base_ppl = compute_ppl(base_model, base_tokenizer, test_texts)
            print(f"[METRIC] Base PPL: {base_ppl:.3f}", flush=True)
            print("[INFO] 测量 Base 模型推理延迟...", flush=True)
            base_latency = measure_latency(base_model, base_tokenizer, prompt_for_latency)
            print(f"[METRIC] Base 延迟: {base_latency:.3f}s", flush=True)
            metrics.update(
                {"base_ppl": base_ppl, "base_latency_s": base_latency}
            )
            del base_model
            torch.cuda.empty_cache()
        except Exception as e:
            print(f"[WARN] Base 模型评估失败: {e}", flush=True)

    # ---------- 6. 可视化 ----------
    models_for_chart = ["Merged FP16", "AWQ INT4"]
    size_values = [merged_size_gb, awq_size_gb]
    ppl_values = [merged_ppl, awq_ppl]
    latency_values = [merged_latency, awq_latency]

    if base_ppl is not None:
        models_for_chart.insert(0, "Base")
        size_values.insert(0, get_dir_size_gb(base_path))
        ppl_values.insert(0, base_ppl)
        latency_values.insert(0, base_latency)

    save_bar_chart(
        models_for_chart,
        size_values,
        "Model Size (GB)",
        "模型大小对比",
        report_dir / "01_model_size_comparison.png",
        colors=["#94a3b8", "#3b82f6", "#16a34a"][: len(models_for_chart)],
    )
    save_bar_chart(
        models_for_chart,
        ppl_values,
        "Perplexity (lower is better)",
        "测试集困惑度对比",
        report_dir / "02_ppl_comparison.png",
        colors=["#94a3b8", "#3b82f6", "#16a34a"][: len(models_for_chart)],
    )
    save_bar_chart(
        models_for_chart,
        latency_values,
        "Latency (s)",
        "单条推理延迟对比",
        report_dir / "03_latency_comparison.png",
        colors=["#94a3b8", "#3b82f6", "#16a34a"][: len(models_for_chart)],
    )

    # ---------- 7. 保存指标 & 同步 WandB ----------
    metrics_path = report_dir / "awq_metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)
    print(f"[INFO] 指标已保存: {metrics_path}", flush=True)

    if wandb_enabled:
        wandb.log(metrics)
        wandb.log(
            {
                "model_size_comparison": wandb.Image(str(report_dir / "01_model_size_comparison.png")),
                "ppl_comparison": wandb.Image(str(report_dir / "02_ppl_comparison.png")),
                "latency_comparison": wandb.Image(str(report_dir / "03_latency_comparison.png")),
            }
        )
        wandb.finish()
        print("[INFO] 指标与图表已同步到 WandB", flush=True)

    # ---------- 8. 生成 Markdown 总结报告 ----------
    summary_md = f"""# AWQ 量化总结报告

## 1. 基本信息

| 项目 | 值 |
|------|-----|
| Merged 模型 | `{args.merged_model}` |
| AWQ 输出目录 | `{args.output_dir}` |
| 量化配置 | bits={args.bits}, group_size={args.group_size} |
| 校准样本数 | {len(calib_texts)} |
| 校准最大长度 | {args.max_calib_length} tokens |
| PPL 测试样本数 | {len(test_texts)} |

## 2. 核心指标

| 指标 | Base | Merged FP16 | AWQ INT4 |
|------|------|-------------|----------|
| 模型大小 (GB) | {get_dir_size_gb(base_path) if base_path.exists() else '-'} | {merged_size_gb} | {awq_size_gb} |
| 测试集 PPL | {base_ppl if base_ppl else '-'} | {merged_ppl:.3f} | {awq_ppl:.3f} |
| 推理延迟 (s) | {base_latency if base_latency else '-'} | {merged_latency:.3f} | {awq_latency:.3f} |
| 量化耗时 (s) | - | - | {quant_time_s:.1f} |
| 体积压缩比 | - | - | {metrics['size_reduction_ratio']}x |

## 3. 效果提升总结

- **体积**: AWQ 模型相比 Merged FP16 缩小约 **{metrics['size_reduction_ratio']}x**，从 {merged_size_gb} GB 降至 {awq_size_gb} GB，
  显著降低部署存储与显存占用。
- **困惑度**: AWQ 后 PPL {awq_ppl:.3f} vs Merged {merged_ppl:.3f}，
  质量损失约 {(awq_ppl - merged_ppl) / merged_ppl * 100:.1f}%，在可接受范围。
- **速度**: AWQ 单条推理延迟 {awq_latency:.3f}s vs Merged {merged_latency:.3f}s，
  约为原来的 {awq_latency / merged_latency * 100:.1f}%。

## 4. 对比图表

![模型大小对比](01_model_size_comparison.png)
![困惑度对比](02_ppl_comparison.png)
![推理延迟对比](03_latency_comparison.png)

## 5. 下一步操作建议

1. **vLLM 部署验证**: 使用 `vllm serve {args.output_dir} --quantization awq --max-model-len 4096 --gpu-memory-utilization 0.85` 启动服务，
   用 `finetune/inference_test.py` 进行真实选品请求压测。
2. **业务指标回测**: 在垂直领域测试集上运行 `finetune/eval_three_models.py`，比较 Base / Merged / AWQ 的偏好对准确率与 margin。
3. **多 batch 吞吐测试**: 使用 `deploy/benchmark_vllm.py` 测试不同并发下的 throughput 与 TPOT，确认 INT4 在真实服务中的收益。
4. **生产灰度**: 若延迟与 PPL 均达标，可将 AWQ 模型作为线上默认路由，保留 FP16 Merged 模型作为回退。
"""
    summary_path = report_dir / "awq_summary_report.md"
    summary_path.write_text(summary_md, encoding="utf-8")
    print(f"[INFO] 总结报告已保存: {summary_path}", flush=True)

    print("\n✅ AWQ 量化与评估全部完成。", flush=True)
    print(f"   量化模型: {output_dir}", flush=True)
    print(f"   报告目录: {report_dir}", flush=True)


if __name__ == "__main__":
    main()
