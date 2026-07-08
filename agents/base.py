# agents/base.py — 所有 Agent 的基类
# 提供通用能力：MCP 工具发现、结果格式格式化

from __future__ import annotations
from typing import Any, Dict, List


class BaseAgent:
    """所有 Agent 的基类"""

    async def execute(self, subtask: Any, mcp_registry: Dict, llm: Any, model: str) -> Dict:
        """由子类实现的具体执行逻辑"""
        raise NotImplementedError

    def _get_tools(self, mcp_registry: Dict) -> List[Dict]:
        """从 MCP 注册表中获取此 Agent 可用的工具"""
        agent_name = self.__class__.__name__.lower().replace("agent", "")
        tools = []
        for server_name, server in mcp_registry.items():
            if hasattr(server, "list_tools"):
                for tool in server.list_tools():
                    tag = tool.get("agent", "all")
                    if tag in (agent_name, "all"):
                        tools.append({
                            "name": tool["name"],
                            "description": tool["description"],
                            "parameters": tool.get("parameters", {}),
                            "server": server_name,
                        })
        return tools
