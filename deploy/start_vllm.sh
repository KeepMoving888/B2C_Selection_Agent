#!/bin/bash
# deploy/start_vllm.sh —— 本地启动 vLLM 推理服务（Linux/macOS）

set -e

MODEL_DIR=${MODEL_DIR:-../models/qwen2.5-7b-ecommerce-awq}
BASE_MODEL_DIR=${BASE_MODEL_DIR:-../models/qwen2.5-7b-base-awq}

echo "Starting vLLM ecommerce model on :8000 ..."
vllm serve "$MODEL_DIR" \
  --quantization awq \
  --max-model-len 4096 \
  --gpu-memory-utilization 0.85 \
  --max-num-seqs 8 \
  --port 8000 \
  --host 0.0.0.0 &

echo "Starting vLLM base model on :8001 ..."
vllm serve "$BASE_MODEL_DIR" \
  --quantization awq \
  --max-model-len 4096 \
  --gpu-memory-utilization 0.85 \
  --max-num-seqs 8 \
  --port 8001 \
  --host 0.0.0.0 &

wait
