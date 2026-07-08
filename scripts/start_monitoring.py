#!/usr/bin/env python3
# ============================================================
# scripts/start_monitoring.py —— 启动 Agent 监控服务
# ============================================================

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from monitoring.server import run_metrics_server


def main():
    port = int(os.environ.get("METRICS_PORT", "9091"))
    collector = run_metrics_server(port)

    if not collector.is_enabled():
        print("[ERROR] prometheus_client 未安装，无法启动 /metrics 服务")
        print("        请执行：pip install prometheus-client>=0.20.0")
        print("        或确认当前 Python 环境已安装全部部署依赖")
        sys.exit(1)

    print(f"[OK] 监控服务已启动：http://localhost:{port}/metrics")
    print("      按 Ctrl+C 停止")
    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("\n[OK] 监控服务已停止")


if __name__ == "__main__":
    main()
