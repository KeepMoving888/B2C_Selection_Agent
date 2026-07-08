#!/usr/bin/env python3
"""
deploy/merge_lora_to_base.py
===========================
将微调后的 LoRA adapter（checkpoint-250）合并到 Qwen2.5-7B base model，
生成完整的 FP16 merged 模型，用于与 AWQ 量化模型做生成时间对比。

输入：
  - models/qwen/Qwen2.5-7B
  - output/qwen2.5-7b-orpo-ecommerce-v1/checkpoint-250

输出：
  - E:/models/qwen2.5-7b-ecommerce-merged-fixed
"""

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

BASE_MODEL = "/mnt/c/Users/Windows/AppData/Roaming/reasonix/global-workspace/cross-border-agent/models/qwen/Qwen2.5-7B"
ADAPTER_PATH = "/mnt/c/Users/Windows/AppData/Roaming/reasonix/global-workspace/cross-border-agent/output/qwen2.5-7b-orpo-ecommerce-v1/checkpoint-250"
OUTPUT_DIR = "/mnt/e/models/qwen2.5-7b-ecommerce-merged-fixed"


def main():
    print("[Merge] Loading base model ...")
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        torch_dtype=torch.float16,
        device_map="auto",
        trust_remote_code=True,
    )
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)

    print("[Merge] Loading LoRA adapter ...")
    model = PeftModel.from_pretrained(model, ADAPTER_PATH)

    print("[Merge] Merging and unloading ...")
    model = model.merge_and_unload()

    print(f"[Merge] Saving merged model to {OUTPUT_DIR} ...")
    model.save_pretrained(OUTPUT_DIR, safe_serialization=True)
    tokenizer.save_pretrained(OUTPUT_DIR)

    print("[Merge] Done.")


if __name__ == "__main__":
    main()
