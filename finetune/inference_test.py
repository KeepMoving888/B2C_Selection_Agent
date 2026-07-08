# ============================================================
# finetune/inference_test.py — 微调后模型推理效果抽样测试
# ============================================================

import os
import random
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import PeftModel


def load_model(adapter_path, base_model_path):
    tokenizer = AutoTokenizer.from_pretrained(adapter_path, trust_remote_code=True)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token

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
    tuned_model = PeftModel.from_pretrained(base_model, adapter_path)
    return tokenizer, base_model, tuned_model


def generate(model, tokenizer, prompt, max_new_tokens=512):
    text = f"<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n"
    inputs = tokenizer(text, return_tensors="pt").to(model.device)
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=True,
            temperature=0.7,
            top_p=0.9,
            eos_token_id=tokenizer.convert_tokens_to_ids("<|im_end|>"),
        )
    generated = tokenizer.decode(outputs[0], skip_special_tokens=False)
    # 去掉输入 prompt 部分
    if "<|im_start|>assistant\n" in generated:
        generated = generated.split("<|im_start|>assistant\n")[-1]
    generated = generated.replace("<|im_end|>", "").strip()
    return generated


def main():
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

    print(f"[Test] Loading models...")
    tokenizer, base_model, tuned_model = load_model(adapter_path, base_model_path)

    # 从训练数据中抽样 3 个 prompt
    data_file = Path(__file__).resolve().parent / "data" / "orpo_chosen_rejected.jsonl"
    import json
    with open(data_file, "r", encoding="utf-8") as f:
        data = [json.loads(line) for line in f]
    random.seed(42)
    samples = random.sample(data, 3)

    output_file = Path(adapter_path).parent / "inference_samples.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        for idx, ex in enumerate(samples, 1):
            prompt = ex["prompt"]
            print(f"\n{'='*64}")
            print(f"[Sample {idx}] Prompt: {prompt[:80]}...")

            print("\n[Base model]")
            base_out = generate(base_model, tokenizer, prompt)
            print(base_out[:500])

            print("\n[Tuned model]")
            tuned_out = generate(tuned_model, tokenizer, prompt)
            print(tuned_out[:500])

            print("\n[Ground truth chosen]")
            print(ex["chosen"][:500])

            f.write(f"\n{'='*64}\n")
            f.write(f"Sample {idx}\nPrompt: {prompt}\n\n")
            f.write(f"[Base model]\n{base_out}\n\n")
            f.write(f"[Tuned model]\n{tuned_out}\n\n")
            f.write(f"[Ground truth chosen]\n{ex['chosen']}\n")

    print(f"\n[Test] Results saved to: {output_file}")


if __name__ == "__main__":
    main()
