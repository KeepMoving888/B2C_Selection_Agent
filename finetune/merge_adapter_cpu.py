#!/usr/bin/env python3
"""
finetune/merge_adapter_cpu.py
=============================
在 CPU 上合并 LoRA adapter 到基座模型，用于显存/内存不足时的兜底方案。

用法：
    python finetune/merge_adapter_cpu.py \
        --base_model /mnt/e/models/qwen/Qwen2.5-7B \
        --adapter /mnt/e/models/qwen2.5-7b-orpo-adapter \
        --output /home/b2cuser/models/qwen2.5-7b-ecommerce-merged
"""

import argparse
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer


def merge_on_cpu(base_model: str, adapter_path: str, output_dir: str):
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    print(f"[1/3] Loading base model on CPU: {base_model}")
    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        torch_dtype=torch.float16,
        device_map="cpu",
        trust_remote_code=True,
        low_cpu_mem_usage=True,
    )
    tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)

    print(f"[2/3] Loading adapter: {adapter_path}")
    model = PeftModel.from_pretrained(model, adapter_path)

    print("[3/3] Merging and unloading adapter...")
    model = model.merge_and_unload()

    print(f"[SAVE] Saving merged model to {output_path}")
    model.save_pretrained(output_path)
    tokenizer.save_pretrained(output_path)
    print(f"[OK] Merged model saved: {output_path}")
    return str(output_path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base_model", default="/mnt/e/models/qwen/Qwen2.5-7B")
    parser.add_argument("--adapter", default="/mnt/e/models/qwen2.5-7b-orpo-adapter")
    parser.add_argument("--output", default="/home/b2cuser/models/qwen2.5-7b-ecommerce-merged")
    args = parser.parse_args()
    merge_on_cpu(args.base_model, args.adapter, args.output)


if __name__ == "__main__":
    main()
