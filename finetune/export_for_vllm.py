#!/usr/bin/env python3
"""
finetune/export_for_vllm.py —— 将 ORPO 微调后的 LoRA adapter 导出为 vLLM 可部署模型

支持两步：
  1. merge_and_unload：把 adapter 合并到基座模型并保存为 FP16
  2. AWQ 量化（可选）：把合并后的模型量化为 4-bit，用于 vLLM 高速推理

用法示例：
  python finetune/export_for_vllm.py \
      --base_model Qwen/Qwen2.5-7B \
      --adapter output/qwen2.5-7b-orpo-ecommerce/adapter \
      --output models/qwen2.5-7b-ecommerce-merged \
      --quantize awq --bits 4
"""

import argparse
import os
import sys
from pathlib import Path


def merge_adapter(base_model: str, adapter_path: str, output_dir: str):
    """合并 LoRA adapter 到基座模型。"""
    try:
        import torch
        from peft import PeftModel
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as e:
        print(f"[ERROR] 缺少依赖：{e}")
        print("        请先安装：pip install torch transformers peft")
        sys.exit(1)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    print(f"[1/3] Loading base model: {base_model}")
    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        torch_dtype=torch.float16,
        device_map="auto",
        trust_remote_code=True,
    )
    tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)

    print(f"[2/3] Loading adapter: {adapter_path}")
    model = PeftModel.from_pretrained(model, adapter_path)

    print("[3/3] Merging and unloading adapter...")
    model = model.merge_and_unload()

    print(f"[SAVE] Saving merged model to {output_path}")
    model.save_pretrained(output_path)
    tokenizer.save_pretrained(output_path)
    return str(output_path)


def _load_calib_data(calib_path: str, max_samples: int = 128):
    """加载本地校准数据，返回文本列表。"""
    import json

    calib_file = Path(calib_path)
    if not calib_file.exists():
        print(f"[WARN] 校准数据不存在: {calib_path}")
        return None

    texts = []
    with open(calib_file, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            ex = json.loads(line)
            prompt = ex.get("prompt", "")
            chosen = ex.get("chosen", "")
            # 与训练时格式保持一致，便于校准
            text = f"<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n{chosen}<|im_end|>"
            texts.append(text)
            if len(texts) >= max_samples:
                break
    print(f"[QUANT] Loaded {len(texts)} local calibration samples from {calib_path}")
    return texts


def quantize_awq(model_path: str, output_dir: str, bits: int = 4, group_size: int = 128,
                 calib_data_path: str = "./finetune/data/orpo_train.jsonl",
                 calib_max_samples: int = 128):
    """使用 AutoAWQ 进行 INT4 量化。"""
    try:
        from awq import AutoAWQForCausalLM
        from transformers import AutoTokenizer
    except ImportError as e:
        print(f"[WARN] 缺少 AutoAWQ：{e}")
        print("       跳过 AWQ 量化，请手动执行：")
        print(f"       python -m awq.quantize --model {model_path} --output {output_dir} "
              f"--bits {bits} --group_size {group_size}")
        return None

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    print(f"[QUANT] Loading model for AWQ {bits}-bit quantization...")
    import torch
    model = AutoAWQForCausalLM.from_pretrained(
        model_path, trust_remote_code=True, safetensors=True, device_map="cuda:0"
    )
    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)

    # 使用本地领域语料作为校准数据，避免联网下载 pile-val-backup
    calib_data = _load_calib_data(calib_data_path, max_samples=calib_max_samples)
    quant_config = {"zero_point": True, "q_group_size": group_size, "w_bit": bits}

    print("[QUANT] Quantizing...")
    if calib_data:
        model.quantize(tokenizer, quant_config=quant_config, calib_data=calib_data)
    else:
        model.quantize(tokenizer, quant_config=quant_config)

    print(f"[SAVE] Saving AWQ model to {output_path}")
    model.save_quantized(output_path)
    tokenizer.save_pretrained(output_path)
    return str(output_path)


def main():
    parser = argparse.ArgumentParser(description="Export fine-tuned model for vLLM")
    parser.add_argument("--base_model", default="E:/models/qwen/Qwen2.5-7B",
                        help="基座模型路径或 HuggingFace / ModelScope 仓库名")
    parser.add_argument("--adapter", default="E:/models/qwen2.5-7b-orpo-adapter",
                        help="LoRA adapter 路径")
    parser.add_argument("--output", default="E:/models/qwen2.5-7b-ecommerce-merged",
                        help="合并后模型保存路径")
    parser.add_argument("--quantize", choices=["none", "awq"], default="none",
                        help="是否进行 AWQ 量化")
    parser.add_argument("--quant_output", default=None,
                        help="AWQ 量化模型保存路径（默认：{output}-awq）")
    parser.add_argument("--bits", type=int, default=4, help="AWQ 量化位数")
    parser.add_argument("--group_size", type=int, default=128, help="AWQ group size")
    parser.add_argument("--calib_data", default="./finetune/data/orpo_train.jsonl",
                        help="AWQ 校准数据路径（本地 jsonl）")
    parser.add_argument("--calib_max_samples", type=int, default=128,
                        help="AWQ 校准样本数量")
    parser.add_argument("--skip_merge", action="store_true",
                        help="若合并模型已存在，跳过合并步骤直接量化")
    args = parser.parse_args()

    if args.skip_merge and Path(args.output).exists():
        print(f"[SKIP] Merged model already exists at {args.output}, skipping merge.")
        merged_path = args.output
    else:
        merged_path = merge_adapter(args.base_model, args.adapter, args.output)

    if args.quantize == "awq":
        quant_dir = args.quant_output or f"{args.output}-awq"
        quantize_awq(merged_path, quant_dir, bits=args.bits, group_size=args.group_size,
                     calib_data_path=args.calib_data, calib_max_samples=args.calib_max_samples)
        serve_path = quant_dir
    else:
        serve_path = merged_path

    print("\n✅ 导出完成。启动 vLLM 示例：")
    print(f"   vllm serve {serve_path} "
          f"{'--quantization awq ' if args.quantize == 'awq' else ''}"
          f"--max-model-len 4096 --gpu-memory-utilization 0.85")


if __name__ == "__main__":
    main()
