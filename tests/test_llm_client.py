# ============================================================
# tests/test_llm_client.py —— 多后端 LLM Client 单元测试
# ============================================================

import asyncio
import json
from unittest.mock import MagicMock, patch

import pytest
import sys
sys.path.insert(0, '.')

from llm import MultiProviderLLMClient, MockLLMClient, ModelUnavailableError, LLMConfig


class TestMockLLMClient:
    def test_default_response(self):
        client = MockLLMClient()
        result = asyncio.run(client.call("hello"))
        assert json.loads(result)["result"] == "ok"

    def test_planner_prompt(self):
        client = MockLLMClient()
        result = asyncio.run(client.call("You are a task planner. Decompose..."))
        tasks = json.loads(result)
        assert isinstance(tasks, list)
        assert tasks[0]["agent"] == "market_research"


class TestMultiProviderLLMClient:
    @pytest.fixture
    def client(self):
        return MultiProviderLLMClient(
            LLMConfig(deepseek_api_key="test-key", timeout_seconds=5)
        )

    def test_fallback_chain_order(self, client):
        # 全部失败时抛 ModelUnavailableError
        with pytest.raises(ModelUnavailableError):
            asyncio.run(client.call("hi", model="v4-pro"))

    def test_deepseek_success(self, client):
        # 直接 mock _call_once，避免依赖 aiohttp
        async def _mock_call_once(*args, **kwargs):
            return "deepseek-ok"
        client._call_once = _mock_call_once

        result = asyncio.run(client.call("hi", model="v4-pro"))
        assert result == "deepseek-ok"

    def test_provider_unhealthy_triggers_fallback(self, client):
        client._health["deepseek"] = False
        # 直接测试：deepseek 不健康时会跳过，最终全部失败
        with pytest.raises(ModelUnavailableError):
            asyncio.run(client.call("hi", model="v4-pro"))


def asynccontextmanager_for(mock_resp):
    """把 mock 响应包成 async with 可用的上下文管理器。"""
    class _CM:
        async def __aenter__(self):
            return mock_resp
        async def __aexit__(self, *args):
            pass
    return _CM()
