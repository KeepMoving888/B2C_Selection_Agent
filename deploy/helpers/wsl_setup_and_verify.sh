#!/usr/bin/env bash
# deploy/_wsl_setup_and_verify.sh
# 一次性在 WSL2 Ubuntu 中完成：启动 vLLM -> 启动 Gateway -> 验证 -> 部署监控
set -e

echo "[INFO] WSL 用户: $(whoami)"
echo "[INFO] 系统: $(cat /etc/os-release | grep PRETTY_NAME | cut -d= -f2 | tr -d '\"')"

# 1. 确保 vLLM 服务启动并就绪
echo "[INFO] 启动 vllm-awq.service ..."
systemctl start vllm-awq.service

echo "[INFO] 等待 vLLM 就绪（轮询 /v1/models）..."
for i in $(seq 1 120); do
    if curl -s --noproxy '*' --max-time 2 http://127.0.0.1:8002/v1/models >/dev/null 2>&1; then
        echo "[OK] vLLM 已就绪"
        curl -s --noproxy '*' --max-time 2 http://127.0.0.1:8002/v1/models | head -c 200
        echo
        break
    fi
    echo "  等待中... ${i}/120"
    sleep 2
done

if ! curl -s --noproxy '*' --max-time 2 http://127.0.0.1:8002/v1/models >/dev/null 2>&1; then
    echo "[ERROR] vLLM 未在 240 秒内就绪"
    journalctl -u vllm-awq.service --no-pager -n 30
    exit 1
fi

# 2. 启动 API Gateway
echo "[INFO] 启动 api-gateway.service ..."
systemctl start api-gateway.service
sleep 3
echo "[INFO] Gateway 健康检查 ..."
curl -s --noproxy '*' --max-time 5 http://127.0.0.1:8080/health | head -c 300 || echo "[WARN] Gateway 健康检查失败"

# 3. 显示服务状态
echo "[INFO] vllm-awq.service 状态:"
systemctl is-active vllm-awq.service
echo "[INFO] api-gateway.service 状态:"
systemctl is-active api-gateway.service

# 4. 尝试一次简单的 chat completion 测试
echo "[INFO] 简单推理测试 ..."
curl -s --noproxy '*' --max-time 60 http://127.0.0.1:8002/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"/home/root/models/qwen2.5-7b-ecommerce-awq-v3","messages":[{"role":"user","content":"hello"}],"max_tokens":20}' | head -c 300

echo "[OK] 验证完成"
