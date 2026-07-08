# ============================================================
# finetune/eval_orpo.py — ORPO 微调效果测试集评估脚本
#
# 使用训练全程不可见的 orpo_test.jsonl 评估微调后的模型泛化能力。
# 要求：orpo_train/val/test 必须按产品严格隔离（由 generate_datasets.py 生成）。
# ============================================================

import os
import json
from pathlib import Path

import torch
from datasets import load_dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import PeftModel


def load_test_data():
    """加载独立测试集（训练全程不可见）"""
    data_file = Path(__file__).resolve().parent / "data" / "orpo_test.jsonl"
    if not data_file.exists():
        raise FileNotFoundError(f"测试集不存在: {data_file}，请先运行 generate_datasets.py 生成")
    ds = load_dataset("json", data_files=str(data_file))["train"]
    return list(ds)


def format_prompt(prompt):
    return f"<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n"


def format_completion(text):
    # 与训练时保持一致：completion 末尾追加结束符
    return f"{text}<|im_end|>" if not text.endswith("<|im_end|>") else text


def compute_logprob(model, tokenizer, text, device="cuda"):
    """计算给定文本的平均负对数似然（NLL）"""
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=768)
    inputs = {k: v.to(device) for k, v in inputs.items()}
    with torch.no_grad():
        outputs = model(**inputs, labels=inputs["input_ids"])
    # 返回每个 token 的平均负对数似然，越小越好
    return outputs.loss.item()


def evaluate(model, tokenizer, test_data, device="cuda", max_samples=None):
    """在独立测试集上评估偏好对齐效果"""
    if max_samples:
        test_data = test_data[:max_samples]

    results = []
    correct = 0

    for idx, ex in enumerate(test_data):
        prompt = ex["prompt"]
        chosen = format_completion(ex["chosen"])
        rejected = format_completion(ex["rejected"])

        chosen_text = format_prompt(prompt) + chosen
        rejected_text = format_prompt(prompt) + rejected

        chosen_nll = compute_logprob(model, tokenizer, chosen_text, device)
        rejected_nll = compute_logprob(model, tokenizer, rejected_text, device)

        # NLL 越小说明模型越偏好该文本
        margin = rejected_nll - chosen_nll
        is_correct = margin > 0
        if is_correct:
            correct += 1

        results.append({
            "idx": idx,
            "chosen_nll": chosen_nll,
            "rejected_nll": rejected_nll,
            "margin": margin,
            "correct": is_correct,
        })

        if (idx + 1) % 20 == 0:
            print(f"  Evaluated {idx + 1}/{len(test_data)} samples...")

    accuracy = correct / len(test_data)
    avg_margin = sum(r["margin"] for r in results) / len(results)
    return accuracy, avg_margin, results


def main():
    # 自动加载 .env
    project_root = Path(__file__).resolve().parent.parent
    env_file = project_root / ".env"
    if env_file.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(dotenv_path=str(env_file), override=True)
        except ImportError:
            pass

    adapter_path = os.getenv("ADAPTER_PATH", "./output/qwen2.5-7b-orpo-ecommerce-v1/adapter")
    base_model_path = os.getenv("BASE_MODEL", "./models/qwen/Qwen2.5-7B")
    device = "cuda" if torch.cuda.is_available() else "cpu"

    print(f"[Eval] Adapter: {adapter_path}")
    print(f"[Eval] Base model: {base_model_path}")
    print(f"[Eval] Device: {device}")

    # 加载独立测试集
    test_data = load_test_data()
    print(f"[Eval] Test samples: {len(test_data)}")
    print("[Eval] NOTE: test set products are strictly disjoint from train/val set")

    # 加载 tokenizer
    tokenizer = AutoTokenizer.from_pretrained(adapter_path, trust_remote_code=True)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token

    # 4-bit 量化加载基础模型
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )
    base_model = AutoModelForCausalLM.from_pretrained(
        base_model_path,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
    )

    # 先评估基座模型
    print("\n[1/2] Evaluating BASE model on test set...")
    base_acc, base_margin, base_results = evaluate(base_model, tokenizer, test_data)
    print(f"  Base model accuracy: {base_acc:.2%}")
    print(f"  Base model avg margin: {base_margin:.4f}")

    # 加载微调后的模型
    print("\n[2/2] Evaluating TUNED model on test set...")
    tuned_model = PeftModel.from_pretrained(base_model, adapter_path)
    tuned_acc, tuned_margin, tuned_results = evaluate(tuned_model, tokenizer, test_data)
    print(f"  Tuned model accuracy: {tuned_acc:.2%}")
    print(f"  Tuned model avg margin: {tuned_margin:.4f}")

    # 汇总
    print("\n" + "=" * 64)
    print("               ORPO 独立测试集评估结果")
    print("=" * 64)
    print(f"  测试集样本数: {len(test_data)}")
    print(f"  基座模型 accuracy:  {base_acc:.2%}")
    print(f"  微调模型 accuracy:  {tuned_acc:.2%}")
    print(f"  基座模型 avg margin: {base_margin:.4f}")
    print(f"  微调模型 avg margin: {tuned_margin:.4f}")
    print(f"  margin 提升: {tuned_margin - base_margin:.4f}")
    print(f"  accuracy 提升: {(tuned_acc - base_acc):.2%}")
    print("=" * 64)

    # 保存结果
    output_dir = Path(adapter_path).parent
    result_file = output_dir / "test_eval_results.json"
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump({
            "test_samples": len(test_data),
            "base_accuracy": base_acc,
            "base_avg_margin": base_margin,
            "tuned_accuracy": tuned_acc,
            "tuned_avg_margin": tuned_margin,
            "margin_improvement": tuned_margin - base_margin,
            "accuracy_improvement": tuned_acc - base_acc,
        }, f, indent=2, ensure_ascii=False)
    print(f"\n[Eval] Results saved to: {result_file}")


if __name__ == "__main__":
    main()
