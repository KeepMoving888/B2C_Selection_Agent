# ============================================================
# finetune/eval_three_models.py — 三模型（Base / Merged / AWQ）独立测试集对比评估
#
# 评估指标：
#   - accuracy：偏好对中 chosen NLL < rejected NLL 的比例
#   - avg margin：mean(rejected_nll - chosen_nll)，越大说明模型越偏好 chosen
# ============================================================

import os
import json
import sys
import gc
from pathlib import Path

import torch
from datasets import load_dataset
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel


def load_test_data(test_path: str):
    data_file = Path(test_path)
    if not data_file.exists():
        raise FileNotFoundError(f"测试集不存在: {data_file}")
    ds = load_dataset("json", data_files=str(data_file))["train"]
    return list(ds)


def format_prompt(prompt: str) -> str:
    return f"<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n"


def format_completion(text: str) -> str:
    return f"{text}<|im_end|>" if not text.endswith("<|im_end|>") else text


def compute_logprob(model, tokenizer, text: str, device: str = "cuda") -> float:
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=768)
    # 若模型被 device_map 分散在 CPU/GPU，input 应跟随 model.embed_tokens 权重所在设备
    try:
        target_device = next(model.parameters()).device
    except Exception:
        target_device = device
    inputs = {k: v.to(target_device) for k, v in inputs.items()}
    with torch.no_grad():
        outputs = model(**inputs, labels=inputs["input_ids"])
    return outputs.loss.item()


def _ensure_awq_model(quant_model_path: str, modelscope_id: str = "Qwen/Qwen2.5-7B-Instruct-AWQ"):
    """若本地 AWQ 模型不存在，从 ModelScope 魔塔下载官方 AWQ 作为参考。"""
    local_path = Path(quant_model_path)
    if local_path.exists():
        return str(local_path)

    print(f"[AWQ] 本地模型不存在: {quant_model_path}")
    print(f"[AWQ] 尝试从 ModelScope 下载: {modelscope_id}")
    try:
        from modelscope import snapshot_download
        downloaded = snapshot_download(modelscope_id, cache_dir=str(local_path.parent))
        print(f"[AWQ] 下载完成: {downloaded}")
        return downloaded
    except Exception as e:
        print(f"[AWQ] ModelScope 下载失败: {e}")
        return None


def evaluate_model(model_path: str, test_data: list, device: str = "cuda",
                   is_awq: bool = False, load_in_8bit: bool = False):
    """加载模型并在独立测试集上评估。"""
    print(f"\n[Load] {model_path}")

    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token

    if is_awq:
        # AWQ 量化模型使用 AutoModelForCausalLM + trust_remote_code 即可加载
        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            device_map="auto",
            trust_remote_code=True,
        )
    elif load_in_8bit:
        # 8-bit 量化加载，降低显存占用，避免 16GB 显卡 OOM
        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            load_in_8bit=True,
            device_map="auto",
            trust_remote_code=True,
        )
    else:
        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            torch_dtype=torch.float16,
            device_map="auto",
            trust_remote_code=True,
        )

    correct = 0
    margins = []
    for idx, ex in enumerate(test_data):
        prompt = ex["prompt"]
        chosen = format_completion(ex["chosen"])
        rejected = format_completion(ex["rejected"])

        chosen_nll = compute_logprob(model, tokenizer, format_prompt(prompt) + chosen, device)
        rejected_nll = compute_logprob(model, tokenizer, format_prompt(prompt) + rejected, device)

        margin = rejected_nll - chosen_nll
        is_correct = margin > 0
        if is_correct:
            correct += 1
        margins.append(margin)

        if (idx + 1) % 20 == 0:
            print(f"  Evaluated {idx + 1}/{len(test_data)} samples...")

    accuracy = correct / len(test_data)
    avg_margin = sum(margins) / len(margins)

    # 清理显存
    del model
    gc.collect()
    torch.cuda.empty_cache()

    return accuracy, avg_margin


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume", action="store_true",
                        help="若存在 model_comparison_results.json，跳过已完成的模型评估")
    args = parser.parse_args()

    # 自动加载 .env
    project_root = Path(__file__).resolve().parent.parent
    env_file = project_root / ".env"
    if env_file.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(dotenv_path=str(env_file), override=True)
        except ImportError:
            pass

    base_model = os.getenv("BASE_MODEL", "./models/qwen/Qwen2.5-7B")
    merged_model = os.getenv("MERGED_MODEL", "./models/qwen2.5-7b-ecommerce-merged")
    quant_model = os.getenv("QUANT_MODEL", "./models/qwen2.5-7b-ecommerce-awq")
    test_data_path = os.getenv("ORPO_TEST_DATA", "./finetune/data/orpo_test.jsonl")
    device = "cuda" if torch.cuda.is_available() else "cpu"

    output_dir = Path("./output/qwen2.5-7b-orpo-ecommerce-v1")
    output_dir.mkdir(parents=True, exist_ok=True)
    result_file = output_dir / "model_comparison_results.json"

    # 尝试读取已有结果
    existing = {}
    if args.resume and result_file.exists():
        with open(result_file, "r", encoding="utf-8") as f:
            existing = json.load(f)
        print(f"[Resume] Loaded existing results from {result_file}")

    print("=" * 64)
    print("  三模型独立测试集对比评估")
    print("=" * 64)
    print(f"Device: {device}")
    print(f"Test data: {test_data_path}")

    test_data = load_test_data(test_data_path)
    print(f"Test samples: {len(test_data)}")

    if "base" in existing:
        print("\n[1/3] BASE model already evaluated, skipping...")
        base_acc = existing["base"]["accuracy"]
        base_margin = existing["base"]["avg_margin"]
        print(f"  Base     accuracy: {base_acc:.2%}, avg margin: {base_margin:.4f}")
    else:
        print("\n[1/3] Evaluating BASE model...")
        base_acc, base_margin = evaluate_model(base_model, test_data, device, is_awq=False)
        print(f"  Base     accuracy: {base_acc:.2%}, avg margin: {base_margin:.4f}")

    if "merged" in existing:
        print("\n[2/3] MERGED/TUNED model already evaluated, skipping...")
        merged_acc = existing["merged"]["accuracy"]
        merged_margin = existing["merged"]["avg_margin"]
        print(f"  Merged   accuracy: {merged_acc:.2%}, avg margin: {merged_margin:.4f}")
    else:
        print("\n[2/3] Evaluating MERGED/TUNED model...")
        merged_acc, merged_margin = evaluate_model(merged_model, test_data, device, is_awq=False, load_in_8bit=True)
        print(f"  Merged   accuracy: {merged_acc:.2%}, avg margin: {merged_margin:.4f}")

    resolved_quant_model = _ensure_awq_model(quant_model)
    quant_exists = resolved_quant_model is not None and Path(resolved_quant_model).exists()
    if quant_exists:
        print("\n[3/3] Evaluating AWQ QUANTIZED model...")
        quant_acc, quant_margin = evaluate_model(resolved_quant_model, test_data, device, is_awq=True)
        print(f"  Quantized accuracy: {quant_acc:.2%}, avg margin: {quant_margin:.4f}")
    else:
        print(f"\n[3/3] AWQ model not available, skipping...")
        quant_acc, quant_margin = None, None

    results = {
        "test_samples": len(test_data),
        "base": {"accuracy": base_acc, "avg_margin": base_margin},
        "merged": {"accuracy": merged_acc, "avg_margin": merged_margin},
    }
    if quant_exists:
        results["quantized"] = {"accuracy": quant_acc, "avg_margin": quant_margin}

    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n[Save] Results saved to {result_file}")

    print("\n" + "=" * 64)
    print("  最终结果")
    print("=" * 64)
    print(f"  Base      | acc={base_acc:.2%} | margin={base_margin:.4f}")
    print(f"  Merged    | acc={merged_acc:.2%} | margin={merged_margin:.4f} (+{merged_margin - base_margin:.4f})")
    if quant_exists:
        print(f"  Quantized | acc={quant_acc:.2%} | margin={quant_margin:.4f} (+{quant_margin - base_margin:.4f}, 相比 merged -{merged_margin - quant_margin:.4f})")
    print("=" * 64)


if __name__ == "__main__":
    main()
