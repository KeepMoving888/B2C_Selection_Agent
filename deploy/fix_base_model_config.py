#!/usr/bin/env python3
"""
deploy/fix_base_model_config.py
==============================
为缺失配置文件的 Qwen2.5-7B base model 补齐 config.json 和 tokenizer 文件。
配置文件从同源的 AWQ 量化模型复制并修改。

输入：
  - /mnt/e/models/qwen2.5-7b-ecommerce-awq-v3 (有完整 config/tokenizer)
  - /mnt/c/.../models/qwen/Qwen2.5-7B (只有 safetensors 权重)

输出：
  - /mnt/c/.../models/qwen/Qwen2.5-7B/config.json
  - /mnt/c/.../models/qwen/Qwen2.5-7B/tokenizer*.json, special_tokens_map.json, vocab.json, merges.txt
"""

import json
import shutil
from pathlib import Path

AWQ_DIR = Path("/mnt/e/models/qwen2.5-7b-ecommerce-awq-v3")
BASE_DIR = Path("/mnt/c/Users/Windows/AppData/Roaming/reasonix/global-workspace/cross-border-agent/models/qwen/Qwen2.5-7B")


def main():
    print(f"[Fix] AWQ dir: {AWQ_DIR}")
    print(f"[Fix] Base dir: {BASE_DIR}")

    # 1. 读取 AWQ config 并生成 base config
    with open(AWQ_DIR / "config.json", "r", encoding="utf-8") as f:
        config = json.load(f)

    # 移除 AWQ 量化相关字段，恢复为 FP16/BF16 base
    config.pop("quantization_config", None)
    config["_name_or_path"] = "Qwen/Qwen2.5-7B"
    config["torch_dtype"] = "bfloat16"
    config["transformers_version"] = "4.49.0"

    with open(BASE_DIR / "config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    print("[Fix] Written config.json")

    # 2. 复制 tokenizer 相关文件
    for fname in [
        "tokenizer.json",
        "tokenizer_config.json",
        "special_tokens_map.json",
        "vocab.json",
        "merges.txt",
    ]:
        src = AWQ_DIR / fname
        dst = BASE_DIR / fname
        if src.exists():
            shutil.copy2(src, dst)
            print(f"[Fix] Copied {fname}")
        else:
            print(f"[Fix] Skip {fname} (not found in AWQ dir)")

    print("[Fix] Done.")


if __name__ == "__main__":
    main()
