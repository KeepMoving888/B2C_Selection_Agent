#!/usr/bin/env bash
# deploy/sync_models_to_wsl.sh
# ============================================================
# 将 E:/models 中的模型同步到 WSL2 原生 ext4，以提升 vLLM 冷启动加载速度。
#
# 前置条件：
#   1. 已在 WSL2 Ubuntu 中挂载 E 盘（默认 /mnt/e）
#   2. 目标目录 /home/$USER/models 存在或可由本脚本创建
#
# 用法（在 WSL2 中执行）：
#   bash deploy/sync_models_to_wsl.sh
# ============================================================

set -e

SRC="/mnt/e/models"
DST="/home/$(whoami)/models"
MODELS=(
    "qwen2.5-7b-ecommerce-awq-v3"
    "qwen2.5-7b-ecommerce-merged"
    "qwen2.5-7b-orpo-adapter"
)

echo "[INFO] Source: $SRC"
echo "[INFO] Destination: $DST"

mkdir -p "$DST"

for model in "${MODELS[@]}"; do
    src_path="$SRC/$model"
    dst_path="$DST/$model"

    if [[ ! -d "$src_path" ]]; then
        echo "[WARN] Source not found, skipping: $src_path"
        continue
    fi

    if [[ -d "$dst_path" ]]; then
        echo "[INFO] Updating $model ..."
        rsync -a --progress "$src_path/" "$dst_path/"
    else
        echo "[INFO] Copying $model (this may take a few minutes) ..."
        cp -r "$src_path" "$dst_path"
    fi
    echo "[OK] $model -> $dst_path"
done

echo ""
echo "[OK] 同步完成。生产 vLLM 服务应使用 $DST 下的路径，例如："
echo "     --model $DST/qwen2.5-7b-ecommerce-awq-v3"
