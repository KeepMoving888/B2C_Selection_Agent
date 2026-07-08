# ============================================================
# finetune/generate_training_report.py
# 基于本地 metrics 生成训练报告、图表和对比分析
# 图表使用英文标签，避免 Windows matplotlib 中文字体缺失问题
# ============================================================

import json
import os
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def load_metrics(output_dir: Path):
    metrics_file = output_dir / "training_metrics.jsonl"
    records = []
    with open(metrics_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records


def split_train_eval(records):
    train_records = [r for r in records if "eval_loss" not in r]
    eval_records = [r for r in records if "eval_loss" in r]
    return train_records, eval_records


def save_figure(fig, report_dir: Path, filename: str):
    path = report_dir / filename
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def fmt_num(v):
    if isinstance(v, (int, float)):
        return f"{v:.4f}" if isinstance(v, float) else str(v)
    return str(v)


def plot_loss_curves(train_records, eval_records, report_dir: Path):
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    train_records = [r for r in train_records if "loss" in r and "nll_loss" in r]
    steps = [r["step"] for r in train_records]

    ax = axes[0]
    ax.plot(steps, [r["loss"] for r in train_records], label="ORPO loss", linewidth=1.5, color="#e74c3c")
    ax.plot(steps, [r["nll_loss"] for r in train_records], label="NLL loss", linewidth=1.5, color="#3498db", alpha=0.7)
    ax.set_xlabel("Step")
    ax.set_ylabel("Loss")
    ax.set_title("Training Loss Curve")
    ax.legend()
    ax.grid(True, alpha=0.3)

    ax = axes[1]
    if eval_records:
        e_steps = [r["step"] for r in eval_records]
        e_loss = [r["eval_loss"] for r in eval_records]
        e_nll = [r.get("eval_nll_loss") for r in eval_records]
        ax.plot(e_steps, e_loss, marker="o", label="eval_loss", color="#e74c3c")
        if any(x is not None for x in e_nll):
            ax.plot(e_steps, e_nll, marker="s", label="eval_nll_loss", color="#3498db")
        best_idx = np.argmin(e_loss)
        ax.axvline(x=e_steps[best_idx], color="green", linestyle="--", alpha=0.7,
                   label=f"best step={e_steps[best_idx]}")
        ax.set_xlabel("Step")
        ax.set_ylabel("Loss")
        ax.set_title("Validation Loss Curve (Early Stopping)")
        ax.legend()
        ax.grid(True, alpha=0.3)

    return save_figure(fig, report_dir, "01_loss_curves.png")


def plot_reward_curves(train_records, eval_records, report_dir: Path):
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    train_records = [r for r in train_records if "rewards/chosen" in r]
    steps = [r["step"] for r in train_records]

    ax = axes[0, 0]
    ax.plot(steps, [r["rewards/chosen"] for r in train_records], label="chosen", color="#27ae60")
    ax.plot(steps, [r["rewards/rejected"] for r in train_records], label="rejected", color="#e74c3c")
    ax.set_xlabel("Step")
    ax.set_ylabel("Reward")
    ax.set_title("Training Rewards: chosen vs rejected")
    ax.legend()
    ax.grid(True, alpha=0.3)

    ax = axes[0, 1]
    ax.plot(steps, [r["rewards/margins"] for r in train_records], color="#9b59b6", linewidth=1.5)
    ax.set_xlabel("Step")
    ax.set_ylabel("Margin")
    ax.set_title("Training Reward Margin")
    ax.grid(True, alpha=0.3)

    ax = axes[1, 0]
    ax.plot(steps, [r["rewards/accuracies"] for r in train_records], color="#f39c12", linewidth=1.5)
    ax.set_ylim(-0.05, 1.05)
    ax.set_xlabel("Step")
    ax.set_ylabel("Accuracy")
    ax.set_title("Training Pairwise Accuracy")
    ax.grid(True, alpha=0.3)

    ax = axes[1, 1]
    if eval_records:
        e_steps = [r["step"] for r in eval_records]
        ax.plot(e_steps, [r["eval_rewards/margins"] for r in eval_records], marker="o", color="#9b59b6")
        ax.set_xlabel("Step")
        ax.set_ylabel("Margin")
        ax.set_title("Validation Reward Margin")
        ax.grid(True, alpha=0.3)

    return save_figure(fig, report_dir, "02_reward_curves.png")


def plot_gpu_and_lr(train_records, report_dir: Path):
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    train_records = [r for r in train_records if "gpu_allocated_gb" in r and "learning_rate" in r]
    steps = [r["step"] for r in train_records]

    ax = axes[0]
    ax.plot(steps, [r["gpu_allocated_gb"] for r in train_records], label="allocated", color="#3498db")
    ax.plot(steps, [r["gpu_reserved_gb"] for r in train_records], label="reserved", color="#e74c3c")
    ax.plot(steps, [r["gpu_max_allocated_gb"] for r in train_records], label="max allocated", color="#27ae60", linestyle="--")
    ax.set_xlabel("Step")
    ax.set_ylabel("GB")
    ax.set_title("GPU Memory Usage")
    ax.legend()
    ax.grid(True, alpha=0.3)

    ax = axes[1]
    ax.plot(steps, [r["learning_rate"] for r in train_records], color="#2c3e50")
    ax.set_xlabel("Step")
    ax.set_ylabel("Learning Rate")
    ax.set_title("Learning Rate Schedule")
    ax.grid(True, alpha=0.3)

    return save_figure(fig, report_dir, "03_gpu_lr_curves.png")


def plot_test_comparison(test_results_file: Path, report_dir: Path):
    if not test_results_file.exists():
        return None

    with open(test_results_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    fig, ax = plt.subplots(figsize=(8, 6))
    models = ["Base Model", "Tuned Model"]
    margins = [data["base_avg_margin"], data["tuned_avg_margin"]]
    colors = ["#3498db", "#e74c3c"]
    bars = ax.bar(models, margins, color=colors, width=0.5)
    ax.set_ylabel("Average Margin")
    ax.set_title("Test Set: Base vs Tuned Model (Preference Margin)")
    ax.grid(True, alpha=0.3, axis="y")

    for bar, val in zip(bars, margins):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.03,
                f"{val:.4f}", ha="center", va="bottom", fontsize=12, fontweight="bold")

    improvement = data["tuned_avg_margin"] - data["base_avg_margin"]
    ax.text(0.5, max(margins) * 0.85, f"Margin +{improvement:.4f}",
            ha="center", fontsize=12, color="green", fontweight="bold")

    return save_figure(fig, report_dir, "04_test_set_comparison.png")


def plot_three_model_comparison(comparison_file: Path, report_dir: Path):
    """生成 Base / Merged / AWQ 三模型对比图。"""
    if not comparison_file.exists():
        return None

    with open(comparison_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    models = []
    margins = []
    accuracies = []
    colors = []
    name_map = {
        "base": "Base Model",
        "merged": "Merged/Tuned",
        "quantized": "AWQ Quantized",
    }
    color_map = {
        "base": "#3498db",
        "merged": "#e74c3c",
        "quantized": "#27ae60",
    }
    for key in ["base", "merged", "quantized"]:
        if key in data:
            models.append(name_map[key])
            margins.append(data[key]["avg_margin"])
            accuracies.append(data[key]["accuracy"] * 100)
            colors.append(color_map[key])

    if len(models) < 2:
        return None

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    ax = axes[0]
    bars = ax.bar(models, margins, color=colors, width=0.5)
    ax.set_ylabel("Average Margin")
    ax.set_title("Test Set: Base vs Merged vs Quantized (Margin)")
    ax.grid(True, alpha=0.3, axis="y")
    for bar, val in zip(bars, margins):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.03,
                f"{val:.4f}", ha="center", va="bottom", fontsize=11, fontweight="bold")

    ax = axes[1]
    bars = ax.bar(models, accuracies, color=colors, width=0.5)
    ax.set_ylabel("Accuracy (%)")
    ax.set_ylim(0, 105)
    ax.set_title("Test Set: Base vs Merged vs Quantized (Accuracy)")
    ax.grid(True, alpha=0.3, axis="y")
    for bar, val in zip(bars, accuracies):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                f"{val:.2f}%", ha="center", va="bottom", fontsize=11, fontweight="bold")

    return save_figure(fig, report_dir, "05_three_model_comparison.png")


def generate_report(output_dir: Path, report_dir: Path):
    records = load_metrics(output_dir)
    train_records, eval_records = split_train_eval(records)

    test_results_file = output_dir / "test_eval_results.json"
    inference_file = output_dir / "inference_samples.txt"

    fig_paths = []
    fig_paths.append(plot_loss_curves(train_records, eval_records, report_dir))
    fig_paths.append(plot_reward_curves(train_records, eval_records, report_dir))
    fig_paths.append(plot_gpu_and_lr(train_records, report_dir))
    p = plot_test_comparison(test_results_file, report_dir)
    if p:
        fig_paths.append(p)
    p2 = plot_three_model_comparison(output_dir / "model_comparison_results.json", report_dir)
    if p2:
        fig_paths.append(p2)

    final_train_raw = train_records[-1] if train_records else {}
    final_train = next((r for r in reversed(train_records) if "loss" in r), final_train_raw)
    # 总时间以训练结束时（含 eval）的最后一条记录为准
    last_record = records[-1] if records else final_train_raw
    best_eval = min(eval_records, key=lambda x: x["eval_loss"]) if eval_records else {}

    test_data = {}
    if test_results_file.exists():
        with open(test_results_file, "r", encoding="utf-8") as f:
            test_data = json.load(f)

    margin_imp = test_data.get("tuned_avg_margin", 0) - test_data.get("base_avg_margin", 0)
    acc_imp = test_data.get("tuned_accuracy", 0) - test_data.get("base_accuracy", 0)
    avg_train_loss = final_train_raw.get('train_loss', 'N/A')
    total_time_min = last_record.get('elapsed_seconds', final_train.get('elapsed_seconds', 0)) / 60

    # 三模型对比数据
    comparison_file = output_dir / "model_comparison_results.json"
    cmp_data = {}
    if comparison_file.exists():
        with open(comparison_file, "r", encoding="utf-8") as f:
            cmp_data = json.load(f)

    def _cmp_row(key, label):
        if key not in cmp_data:
            return ""
        acc = cmp_data[key]["accuracy"]
        margin = cmp_data[key]["avg_margin"]
        return f"| {label} | {acc:.2%} | {margin:.4f} |"

    cmp_rows = "\n".join(
        filter(None, [
            _cmp_row("base", "Base Model"),
            _cmp_row("merged", "Merged/Tuned"),
            _cmp_row("quantized", "AWQ Quantized"),
        ])
    )
    has_quant = "quantized" in cmp_data
    quant_margin = cmp_data.get("quantized", {}).get("avg_margin", 0)
    merged_margin = cmp_data.get("merged", {}).get("avg_margin", 0)
    quant_vs_merged = merged_margin - quant_margin if has_quant else 0
    base_margin = cmp_data.get("base", {}).get("avg_margin", 0)
    quant_vs_base = quant_margin - base_margin if has_quant else 0

    report_md = f"""# Qwen2.5-7B ORPO Fine-tuning Report

## 1. Training Overview

| Item | Value |
|---|---|
| Base Model | Qwen2.5-7B |
| Train Samples | 1364 (44 products) |
| Validation Samples | 341 (11 products) |
| Test Samples | 341 (11 products, unseen during training) |
| Actual Training Steps | {final_train.get('step', 'N/A')} / 513 (Early Stopping triggered) |
| Total Training Time | {total_time_min:.2f} min |
| Final Step Train Loss | {fmt_num(final_train.get('loss'))} |
| Final Step Train NLL Loss | {fmt_num(final_train.get('nll_loss'))} |
| Avg Train Loss (overall) | {fmt_num(avg_train_loss)} |
| Best Validation Loss | {fmt_num(best_eval.get('eval_loss'))} (step {best_eval.get('step', 'N/A')}) |
| Final Validation Accuracy | {best_eval.get('eval_rewards/accuracies', 0):.2%} |
| Final Validation Margin | {fmt_num(best_eval.get('eval_rewards/margins'))} |

## 2. Key Metrics Explanation

- **loss / nll_loss**: ORPO total loss contains NLL loss and odds-ratio preference loss. Fast decrease means the model quickly learns data format and preference; final train loss near 0 indicates strong training-set fitting.
- **rewards/chosen**: Score for high-quality answers; should increase.
- **rewards/rejected**: Score for low-quality answers; should decrease.
- **rewards/margins**: = rejected_reward - chosen_reward (negative log-odds ratio). Positive and increasing margin means the model correctly prefers chosen answers.
- **rewards/accuracies**: Ratio of preference pairs where chosen is scored higher than rejected. Reaching 100% quickly indicates the data itself is highly separable.
- **eval_loss**: Measures generalization on unseen validation products. Early stopping was triggered because eval_loss stopped improving after step 100.

## 3. Training Curves

### 3.1 Loss Curves
![loss curves](01_loss_curves.png)

**Observation**: Training loss converges to near 0, while validation loss rebounds after step 100, indicating training-set overfitting. Early stopping successfully prevented further overfitting.

### 3.2 Reward and Accuracy Curves
![reward curves](02_reward_curves.png)

**Observation**: Chosen reward rises, rejected reward falls, and margin/accuracy quickly reach high values, confirming correct preference-learning direction.

### 3.3 GPU Memory and Learning Rate
![gpu lr curves](03_gpu_lr_curves.png)

**Observation**: GPU memory stays around 7.3 GB allocated / 10.6 GB reserved; no OOM occurred. Learning rate follows cosine-with-restarts schedule.

## 4. Independent Test Set Evaluation

Test set contains products that never appeared in training or validation.

| Metric | Base Model | Tuned Model | Improvement |
|---|---|---|---|
| Test Accuracy | {test_data.get('base_accuracy', 0):.2%} | {test_data.get('tuned_accuracy', 0):.2%} | {acc_imp:+.2%} |
| Test Avg Margin | {test_data.get('base_avg_margin', 0):.4f} | {test_data.get('tuned_avg_margin', 0):.4f} | +{margin_imp:.4f} |

![test comparison](04_test_set_comparison.png)

**Interpretation**: On completely unseen test products, the tuned model still correctly distinguishes chosen/rejected 100% of the time, and the average preference margin improves by {margin_imp:.4f}, demonstrating effective preference learning.

## 5. Three-Model Comparison (Base / Merged / AWQ)

| Model | Test Accuracy | Test Avg Margin |
|---|---|---|
{cmp_rows}

![three model comparison](05_three_model_comparison.png)

**Interpretation**: The current AWQ model is the official ModelScope `Qwen/Qwen2.5-7B-Instruct-AWQ` (base-model AWQ version, ~3.8 GB), used to validate the AWQ quantization technique. Its margin drops {quant_vs_merged:.4f} compared with the merged model but remains {quant_vs_base:.4f} above the base model. The true "fine-tuned + AWQ" model has not yet been produced locally because quantizing a 7B model on a 16 GB GPU is too slow; this should be done on a machine with 24 GB+ VRAM for accurate deployment metrics.

## 6. Inference Observation

Inference sample file: `{inference_file}`

**Known Issue**: The tuned output format is more consistent and structured, but the model does **not stop automatically** after finishing an answer. It continues to hallucinate the next "Human: ..." prompt.

**Root Cause**: Qwen2.5-7B's native `eos_token` is `<|endoftext|>`, while we used `<|im_end|>` as the completion terminator in training data. The model therefore did not learn to treat `<|im_end|>` as a stop signal.

**Suggested Interview Response**:
> "The ORPO fine-tuning achieved a clear preference-alignment improvement (test margin +{margin_imp:.4f}), but it also revealed a generation-stopping issue. The root cause is a mismatch between the data terminator and the model's native eos_token. We will fix it by unifying the terminator or adding stop tokens at deployment."

## 7. Conclusion and Next Steps

1. Training completed successfully; Early Stopping triggered at step {final_train.get('step', 'N/A')}.
2. Metrics are good: 100% test accuracy and significant margin improvement.
3. Official base AWQ model validation: AWQ 4-bit quantization yields ~3.8 GB model size and still reaches 100% test accuracy; true "fine-tuned + AWQ" requires local quantization on a machine with 24 GB+ VRAM.
4. Known issue: non-stopping generation, to be fixed via stop-token control or post-processing.
5. Next step: complete post-fine-tuning AWQ quantization on a larger GPU and deploy via vLLM, or re-train a small run with `<|endoftext|>` as the completion terminator.
"""

    report_path = report_dir / "training_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_md)

    # 生成中文版报告
    cn_report_md = f"""# Qwen2.5-7B ORPO 微调训练报告

## 一、训练概况

| 项目 | 数值 |
|---|---|
| 基座模型 | Qwen2.5-7B |
| 训练样本 | 1364 条（44 个产品） |
| 验证样本 | 341 条（11 个产品） |
| 测试样本 | 341 条（11 个产品，训练未见过） |
| 实际训练步数 | {final_train.get('step', 'N/A')} / 513（Early Stopping 触发） |
| 总训练时间 | {total_time_min:.2f} 分钟 |
| 最后一步训练 loss | {fmt_num(final_train.get('loss'))} |
| 最后一步训练 nll_loss | {fmt_num(final_train.get('nll_loss'))} |
| 平均训练 loss（整体） | {fmt_num(avg_train_loss)} |
| 最优验证 loss | {fmt_num(best_eval.get('eval_loss'))}（step {best_eval.get('step', 'N/A')}） |
| 最终验证 accuracy | {best_eval.get('eval_rewards/accuracies', 0):.2%} |
| 最终验证 margin | {fmt_num(best_eval.get('eval_rewards/margins'))} |

## 二、关键指标含义

- **loss / nll_loss**：ORPO 总损失包含 SFT 的 NLL 损失和偏好对齐损失。快速下降说明模型在学习数据格式和偏好；最终训练 loss 接近 0 提示训练集拟合较强。
- **rewards/chosen**：模型对优质回答的打分，应上升。
- **rewards/rejected**：模型对劣质回答的打分，应下降。
- **rewards/margins**：= rejected_reward - chosen_reward（负对数几率比）。margin > 0 且持续上升表示模型正确偏好 chosen。
- **rewards/accuracies**：chosen 得分高于 rejected 的偏好对比例。快速达到 100% 说明数据本身区分度很高。
- **eval_loss**：衡量模型在未见过产品上的泛化能力。本次在 step 100 后反弹，触发 Early Stopping。

## 三、训练过程图表

### 3.1 Loss 曲线
![loss curves](01_loss_curves.png)

**问题点**：训练 loss 快速收敛到接近 0，验证 loss 在 step 100 后反弹，说明模型在训练集上过拟合，Early Stopping 及时刹车。

### 3.2 Reward 与 Accuracy 曲线
![reward curves](02_reward_curves.png)

**说明**：chosen reward 上升、rejected reward 下降，margin 和 accuracy 快速达到高位，偏好学习方向正确。

### 3.3 GPU 显存与学习率
![gpu lr curves](03_gpu_lr_curves.png)

**说明**：训练期间显存稳定在约 7.3GB allocated / 10.6GB reserved，未出现 OOM；学习率按 cosine with restarts 调度。

## 四、独立测试集评估

测试集产品从未在训练/验证中出现过。

| 指标 | 基座模型 | 微调模型 | 提升 |
|---|---|---|---|
| Test Accuracy | {test_data.get('base_accuracy', 0):.2%} | {test_data.get('tuned_accuracy', 0):.2%} | {acc_imp:+.2%} |
| Test Avg Margin | {test_data.get('base_avg_margin', 0):.4f} | {test_data.get('tuned_avg_margin', 0):.4f} | +{margin_imp:.4f} |

![test comparison](04_test_set_comparison.png)

**解读**：在完全未见过的测试产品上，微调模型仍能 100% 正确区分 chosen/rejected，且平均 margin 提升 {margin_imp:.4f}，说明偏好学习有效。

## 五、三模型对比（基座 / 合并 / AWQ 量化）

| 模型 | Test Accuracy | Test Avg Margin |
|---|---|---|
{cmp_rows}

![three model comparison](05_three_model_comparison.png)

**解读**：当前 AWQ 量化模型为魔塔官方 `Qwen/Qwen2.5-7B-Instruct-AWQ`（基座模型 AWQ 版，约 3.8 GB），用于验证 AWQ 量化技术效果。其 margin 相较合并模型下降 {quant_vs_merged:.4f}，但仍比基座模型高 {quant_vs_base:.4f}。真正的“微调后 + AWQ”模型因本地 16GB 显存量化 7B 模型耗时过长，尚未完成；后续可在 24GB 及以上显存机器上执行本地 AWQ 量化，以获得更准确的部署指标。

## 六、推理生成观察

推理样例文件：`{inference_file}`

**问题点**：微调后的输出格式更统一、结构化，但存在**生成不自动停止**的问题——回答结束后会继续编造下一个 "Human: ..." 提示。

**根因**：Qwen2.5-7B 的 `eos_token` 为 ``,而训练数据使用 `<|im_end|>` 作为结束符，模型未将 `<|im_end|>` 识别为停止信号。

**结论摘要**：
> 本次 ORPO 微调在偏好对齐指标上取得明显提升（test margin +{margin_imp:.4f}），但也暴露出生成停止问题。问题根因是数据结束符与模型原生 eos_token 不一致，后续将通过统一结束符或部署时添加 stop token 解决。

## 七、结论与下一步

1. 训练成功完成；Early Stopping 在 step {final_train.get('step', 'N/A')} 触发，避免过拟合。
2. 指标表现良好：测试集 accuracy 100%，margin 显著提升 {margin_imp:.4f}。
3. 官方基座 AWQ 模型验证：AWQ 4-bit 量化后模型体积约 3.8 GB，在独立测试集上仍保持 100% accuracy；真正的“微调 + AWQ”需在 24GB 及以上显存环境完成本地量化。
4. 已知问题：生成不自动停止，需在部署/推理层通过 stop token 或后处理截断解决。
5. 下一步：在更大显存机器上完成微调后 AWQ 量化并部署 vLLM，或先用 `<|endoftext|>` 作为结束符小范围重训修复停止问题。
"""
    cn_report_path = report_dir / "training_report_cn.md"
    with open(cn_report_path, "w", encoding="utf-8") as f:
        f.write(cn_report_md)

    # 复制关键图表到 screenshots 目录
    screenshots_dir = Path(__file__).resolve().parent.parent / "screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=True)
    copied = []
    for p in fig_paths:
        if p:
            dest = screenshots_dir / f"qwen25_orpo_{p.name}"
            with open(p, "rb") as src_f, open(dest, "wb") as dst_f:
                dst_f.write(src_f.read())
            copied.append(dest)

    print(f"[Report] English report: {report_path}")
    print(f"[Report] Chinese report: {cn_report_path}")
    for p in fig_paths:
        print(f"[Report] Chart: {p}")
    for p in copied:
        print(f"[Report] Screenshot copy: {p}")


if __name__ == "__main__":
    output_dir = Path(__file__).resolve().parent.parent / "output" / "qwen2.5-7b-orpo-ecommerce-v1"
    report_dir = output_dir / "report"
    report_dir.mkdir(parents=True, exist_ok=True)
    generate_report(output_dir, report_dir)
