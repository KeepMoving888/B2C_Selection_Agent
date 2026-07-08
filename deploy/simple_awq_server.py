#!/usr/bin/env python3
"""
deploy/simple_awq_server.py
===========================
Windows 下可直接运行的 AWQ INT4 推理服务（Flask 版，OpenAI-compatible）。

注意：这不是 vLLM，而是基于 transformers + AutoAWQ 的简化服务，用于在 Windows 上
快速验证 AWQ 量化模型的部署效果。生产环境推荐迁移到 Linux/WSL + vLLM。

启动：
    python deploy/simple_awq_server.py

接口：
    POST /v1/chat/completions
"""

import json
import os
import time
import warnings
from pathlib import Path
from threading import Lock

import torch
from flask import Flask, Response, request, jsonify
from transformers import AutoModelForCausalLM, AutoTokenizer

warnings.filterwarnings("ignore")

app = Flask(__name__)

# --------------------------- 配置 ---------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = os.getenv("AWQ_MODEL_PATH", "E:/models/qwen2.5-7b-ecommerce-awq-v3")
MAX_MODEL_LEN = int(os.getenv("MAX_MODEL_LEN", "4096"))
PORT = int(os.getenv("SERVER_PORT", "8000"))

# --------------------------- 加载模型 ---------------------------
print(f"[Server] Loading AWQ model from {MODEL_PATH} ...", flush=True)
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, trust_remote_code=True)
if tokenizer.pad_token_id is None:
    tokenizer.pad_token = tokenizer.eos_token

model = AutoModelForCausalLM.from_pretrained(
    MODEL_PATH,
    device_map="auto",
    trust_remote_code=True,
)
model.eval()
print("[Server] Model loaded.", flush=True)

# 简单请求统计
request_lock = Lock()
request_count = 0

def format_chat_prompt(messages: list) -> str:
    """把 OpenAI 格式的 messages 拼成 Qwen chat template 文本。"""
    prompt = ""
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        prompt += f"<|im_start|>{role}\n{content}<|im_end|>\n"
    prompt += "<|im_start|>assistant\n"
    return prompt


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "model": MODEL_PATH})


@app.route("/v1/chat/completions", methods=["POST"])
def chat_completions():
    global request_count
    data = request.get_json(force=True)
    messages = data.get("messages", [])
    max_tokens = int(data.get("max_tokens", 256))
    temperature = float(data.get("temperature", 0.7))
    top_p = float(data.get("top_p", 0.9))
    stream = data.get("stream", False)

    prompt_text = format_chat_prompt(messages)
    inputs = tokenizer(prompt_text, return_tensors="pt", truncation=True, max_length=MAX_MODEL_LEN)
    device = next(model.parameters()).device
    inputs = {k: v.to(device) for k, v in inputs.items()}

    start = time.time()
    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            do_sample=temperature > 0,
            temperature=temperature if temperature > 0 else None,
            top_p=top_p,
            eos_token_id=tokenizer.convert_tokens_to_ids("<|im_end|>"),
            pad_token_id=tokenizer.pad_token_id,
        )
    latency_s = time.time() - start

    generated_ids = output_ids[0][inputs["input_ids"].shape[1]:]
    generated_text = tokenizer.decode(generated_ids, skip_special_tokens=True)

    with request_lock:
        request_count += 1
        current_count = request_count

    response = {
        "id": f"chatcmpl-{current_count}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": MODEL_PATH,
        "usage": {
            "prompt_tokens": inputs["input_ids"].shape[1],
            "completion_tokens": len(generated_ids),
            "total_tokens": inputs["input_ids"].shape[1] + len(generated_ids),
        },
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": generated_text},
                "finish_reason": "stop",
            }
        ],
        "latency_s": latency_s,
    }

    if stream:
        def stream_gen():
            yield f"data: {json.dumps(response, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        return Response(stream_gen(), mimetype="text/plain")

    return jsonify(response)


if __name__ == "__main__":
    # threaded=True 允许并发请求（GIL 限制，非真正并行，但足够压测）
    app.run(host="0.0.0.0", port=PORT, threaded=True)
