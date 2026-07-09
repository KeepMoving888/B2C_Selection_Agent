#!/usr/bin/env bash
# 防止 WSL 实例在空闲时自动关闭，保持服务持续运行
while true; do
    sleep 60
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] keepalive"
done
