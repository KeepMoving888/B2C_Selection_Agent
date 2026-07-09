#!/usr/bin/env bash
# deploy/install_systemd_services.sh
# ============================================================
# 在 WSL2 Ubuntu 中安装 vLLM + API Gateway 的 systemd 服务。
#
# 前置条件：
#   1. 已安装 vLLM 与项目 Python 依赖（推荐虚拟环境 /opt/b2c-venv）
#   2. 模型已放置到 /home/root/models/ 或 /mnt/e/models/
#   3. 以 sudo 权限运行
#
# 用法：
#   sudo bash deploy/install_systemd_services.sh
# ============================================================

set -e

PROJECT_DIR="/mnt/c/Users/Windows/AppData/Roaming/reasonix/global-workspace/cross-border-agent"
SERVICE_DIR="/etc/systemd/system"

# 将 Windows 路径转换为 WSL 路径的辅助函数
winpath_to_wsl() {
    python3 - <<'PY'
import os, sys
p = os.path.abspath(os.getcwd())
if p.startswith('C:'):
    print('/mnt/c' + p[2:].replace('\\', '/'))
else:
    print(p.replace('\\', '/'))
PY
}

if [[ "$(id -u)" != "0" ]]; then
    echo "[ERROR] 请使用 sudo 运行本脚本"
    exit 1
fi

echo "[INFO] 检查 WSL ext4 模型路径 ..."
WSL_MODEL_DIR="/home/$(whoami)/models"
mkdir -p "$WSL_MODEL_DIR"
if [[ ! -d "$WSL_MODEL_DIR/qwen2.5-7b-ecommerce-awq-v3" ]]; then
    echo "[WARN] 未在 $WSL_MODEL_DIR 找到模型。建议先运行同步脚本："
    echo "       bash ${PROJECT_DIR}/deploy/sync_models_to_wsl.sh"
    echo "[WARN] 若坚持使用 /mnt/e/models，请手动编辑 vllm-awq.service 中的 --model 路径。"
fi

echo "[INFO] 安装 vLLM AWQ 系统服务 ..."
cp "${PROJECT_DIR}/deploy/vllm-awq.service" "${SERVICE_DIR}/"

echo "[INFO] 安装 API Gateway 系统服务 ..."
cp "${PROJECT_DIR}/deploy/api-gateway.service" "${SERVICE_DIR}/"

echo "[INFO] 重新加载 systemd daemon ..."
systemctl daemon-reload

echo "[INFO] 启用开机自启 ..."
systemctl enable vllm-awq.service
systemctl enable api-gateway.service

echo ""
echo "[OK] 服务安装完成。接下来请执行："
echo ""
echo "  1. 检查模型路径："
echo "     ls -lh /home/root/models/qwen2.5-7b-ecommerce-awq-v3"
echo ""
echo "  2. 如需从 E 盘加载模型，请修改 /etc/systemd/system/vllm-awq.service 中的 --model 路径为 /mnt/e/models/..."
echo ""
echo "  3. 如需接入 DeepSeek，编辑 /etc/systemd/system/api-gateway.service，取消 DEEPSEEK_API_KEY 注释并填入 key"
echo ""
echo "  4. 启动服务："
echo "     sudo systemctl start vllm-awq.service"
echo "     sudo systemctl start api-gateway.service"
echo ""
echo "  5. 查看状态："
echo "     sudo systemctl status vllm-awq.service"
echo "     sudo systemctl status api-gateway.service"
echo ""
echo "  6. 查看日志："
echo "     sudo journalctl -u vllm-awq.service -f"
echo "     sudo journalctl -u api-gateway.service -f"
