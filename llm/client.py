# ============================================================
# llm/client.py —— 多后端 LLM 统一调用客户端
#
# 支持：
#   - DeepSeek API（v4-pro / v4-flash）
#   - 本地 vLLM OpenAI 兼容服务（qwen2.5-7b-orpo / qwen2.5-7b-base）
#   - Mock 客户端（测试用）
#
# 设计原则：
#   1. 与现有 Agent 接口兼容：await llm.call(prompt, model=...)
#   2. 模型名由 ModelRouter 决定，客户端负责解析为实际提供商
#   3. 单个模型失败时自动按降级链切换，不中断 Agent 执行
# ============================================================

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from llm.config import LLMConfig

if TYPE_CHECKING:
    from monitoring.metrics import MetricsCollector


class ModelUnavailableError(RuntimeError):
    """当前模型/后端不可用，可触发上层降级。"""
    pass


class MockLLMClient:
    """测试用 Mock LLM，保持与生产客户端相同接口。"""

    def __init__(self, response: str = '{"result": "ok"}'):
        self.response = response

    async def call(self, prompt: str, model: str = "", tools: list = None) -> str:
        # 允许测试通过 prompt 关键词返回不同内容
        p = prompt.lower()
        if "task planner" in p or "decompose" in p:
            return (
                '[{"id":"m1","agent":"market_research","action":"analyze market",'
                '"input_data":{},"depends_on":[]},'
                '{"id":"s1","agent":"supply_chain","action":"find suppliers",'
                '"input_data":{},"depends_on":[]}]'
            )
        if "product selection report" in p or "executive_summary" in p:
            return (
                '{"executive_summary":"Promising","overall_score":78,'
                '"dimension_scores":{"market":32,"supply":22,"profit":16,"risk":8},'
                '"detailed_analysis":{},"risk_warnings":[],'
                '"action_recommendations":[],"data_sources":[]}'
            )
        return self.response


class MultiProviderLLMClient:
    """多后端 LLM 客户端：DeepSeek / 本地 vLLM / Mock。"""

    # 逻辑模型 -> 后端提供商
    PROVIDER_MAP = {
        "v4-pro": "deepseek",
        "v4-flash": "deepseek",
        "qwen2.5-7b-orpo": "vllm_orpo",
        "qwen2.5-7b-base": "vllm_base",
    }

    # 降级链：上层模型失败时自动尝试下层
    FALLBACK_CHAIN = {
        "v4-pro": ["v4-pro", "qwen2.5-7b-orpo", "qwen2.5-7b-base"],
        "v4-flash": ["v4-flash", "qwen2.5-7b-orpo", "qwen2.5-7b-base"],
        "qwen2.5-7b-orpo": ["qwen2.5-7b-orpo", "qwen2.5-7b-base"],
        "qwen2.5-7b-base": ["qwen2.5-7b-base"],
    }

    def __init__(
        self,
        config: Optional[LLMConfig] = None,
        metrics_collector: Optional["MetricsCollector"] = None,
    ):
        self.config = config or LLMConfig()
        self._metrics = metrics_collector
        self._health: Dict[str, bool] = {
            "deepseek": True,
            "vllm_orpo": True,
            "vllm_base": True,
        }
        self._session: Optional[Any] = None

    async def _get_session(self):
        try:
            import aiohttp
        except ImportError as e:
            raise ModelUnavailableError(f"aiohttp not installed: {e}")
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    def _provider_for(self, model: str) -> str:
        return self.PROVIDER_MAP.get(model, "mock")

    def _actual_model(self, model: str) -> str:
        """将逻辑模型名映射为后端真实模型名。"""
        if model == "v4-pro":
            return self.config.deepseek_premium_model
        if model == "v4-flash":
            return self.config.deepseek_flash_model
        # vLLM 服务通常不校验模型名，直接使用逻辑名即可
        return model

    def _endpoint(self, provider: str) -> str:
        if provider == "deepseek":
            return f"{self.config.deepseek_base_url}/chat/completions"
        if provider == "vllm_orpo":
            return f"{self.config.vllm_orpo_url}/chat/completions"
        if provider == "vllm_base":
            return f"{self.config.vllm_base_url}/chat/completions"
        raise ModelUnavailableError(f"Unknown provider: {provider}")

    def _headers(self, provider: str) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if provider == "deepseek":
            key = self.config.deepseek_api_key
            if not key:
                raise ModelUnavailableError("DEEPSEEK_API_KEY not configured")
            headers["Authorization"] = f"Bearer {key}"
        return headers

    async def call(self, prompt: str, model: str = "", tools: list = None) -> str:
        """调用 LLM。失败时按降级链自动切换模型。"""
        chain = self.FALLBACK_CHAIN.get(model, [model])
        last_error: Optional[Exception] = None

        for attempt_model in chain:
            provider = self._provider_for(attempt_model)
            if not self._health.get(provider, True):
                continue
            start = time.time()
            try:
                response = await self._call_once(
                    prompt, attempt_model, provider, tools
                )
                if self._metrics:
                    self._metrics.record_llm_request(
                        model=attempt_model,
                        duration_seconds=time.time() - start,
                        success=True,
                    )
                return response
            except ModelUnavailableError as e:
                last_error = e
                self._health[provider] = False
                if self._metrics:
                    self._metrics.record_llm_request(
                        model=attempt_model,
                        duration_seconds=time.time() - start,
                        success=False,
                    )
                continue
            except Exception as e:
                # 网络/超时等也视为后端不可用，触发降级
                last_error = e
                self._health[provider] = False
                if self._metrics:
                    self._metrics.record_llm_request(
                        model=attempt_model,
                        duration_seconds=time.time() - start,
                        success=False,
                    )
                continue

        raise ModelUnavailableError(
            f"All model providers failed for '{model}'. Last error: {last_error}"
        )

    async def _call_once(
        self,
        prompt: str,
        model: str,
        provider: str,
        tools: Optional[list],
    ) -> str:
        session = await self._get_session()
        payload: Dict = {
            "model": self._actual_model(model),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
        }
        if tools:
            payload["tools"] = tools

        try:
            import aiohttp
            timeout = aiohttp.ClientTimeout(total=self.config.timeout_seconds)
            async with session.post(
                self._endpoint(provider),
                headers=self._headers(provider),
                json=payload,
                timeout=timeout,
            ) as resp:
                text = await resp.text()
                if resp.status != 200:
                    raise ModelUnavailableError(
                        f"{provider} returned {resp.status}: {text[:200]}"
                    )
                data = json.loads(text)
                choices = data.get("choices", [])
                if not choices:
                    raise ModelUnavailableError(f"{provider} returned empty choices")
                content = choices[0].get("message", {}).get("content", "")
                if not content:
                    raise ModelUnavailableError(f"{provider} returned empty content")
                return content
        except aiohttp.ClientError as e:
            raise ModelUnavailableError(f"{provider} connection error: {e}")

    def mark_healthy(self, provider: str):
        self._health[provider] = True

    def mark_unhealthy(self, provider: str):
        self._health[provider] = False
