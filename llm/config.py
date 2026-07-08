# ============================================================
# llm/config.py —— 多后端 LLM 配置
# ============================================================

from dataclasses import dataclass, field
import os


@dataclass
class LLMConfig:
    """LLM 多后端配置，支持环境变量覆盖。"""

    # DeepSeek API
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    # DeepSeek V4 官方模型 ID（2026-04 发布）。
    # 旧别名 deepseek-reasoner / deepseek-chat 计划于 2026-07-24 退役。
    deepseek_premium_model: str = "deepseek-v4-pro"     # 复杂推理
    deepseek_flash_model: str = "deepseek-v4-flash"     # 高性价比

    # 本地 vLLM 服务（OpenAI 兼容）
    vllm_orpo_url: str = "http://localhost:8000/v1"     # 领域微调模型
    vllm_base_url: str = "http://localhost:8001/v1"     # 基础保底模型

    # 通用参数
    timeout_seconds: float = 60.0
    max_retries: int = 2

    def __post_init__(self):
        self.deepseek_api_key = self.deepseek_api_key or os.environ.get("DEEPSEEK_API_KEY", "")
        self.deepseek_base_url = self.deepseek_base_url or os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
        self.deepseek_premium_model = self.deepseek_premium_model or os.environ.get("DEEPSEEK_PREMIUM_MODEL", "deepseek-v4-pro")
        self.deepseek_flash_model = self.deepseek_flash_model or os.environ.get("DEEPSEEK_FLASH_MODEL", "deepseek-v4-flash")
        self.vllm_orpo_url = self.vllm_orpo_url or os.environ.get("VLLM_ORPO_URL", "http://localhost:8000/v1")
        self.vllm_base_url = self.vllm_base_url or os.environ.get("VLLM_BASE_URL", "http://localhost:8001/v1")
        self.timeout_seconds = float(os.environ.get("LLM_TIMEOUT_SECONDS", self.timeout_seconds))
        self.max_retries = int(os.environ.get("LLM_MAX_RETRIES", self.max_retries))
