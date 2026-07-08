# ============================================================
# scripts/upload_modelscope_merged.py — 上传合并模型到 ModelScope
# ============================================================

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from modelscope.hub.api import HubApi

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

MODEL_DIR = r"E:\models\qwen2.5-7b-ecommerce-merged"
MODEL_ID = "keepzhe/qwen2.5-7b-ecommerce-merged"
TOKEN = os.getenv("MODELSCOPE_ACCESS_TOKEN", "").strip()


def main():
    if not TOKEN:
        print("[ERROR] 未找到 MODELSCOPE_ACCESS_TOKEN，请写入 .env 文件")
        sys.exit(1)

    api = HubApi()
    api.login(TOKEN)
    print(f"[INFO] ModelScope 登录成功，开始上传 {MODEL_ID}")
    print(f"[INFO] 本地模型目录: {MODEL_DIR}")

    api.push_model(
        model_id=MODEL_ID,
        model_dir=MODEL_DIR,
        commit_message="Upload merged FP16 model",
    )
    print(f"[INFO] 模型 {MODEL_ID} 上传完成")


if __name__ == "__main__":
    main()
