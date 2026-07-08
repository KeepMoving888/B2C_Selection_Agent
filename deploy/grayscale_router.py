#!/usr/bin/env python3
"""
deploy/grayscale_router.py
==========================
生产灰度路由：根据任务复杂度与模型状态，将流量分配到不同推理后端。

路由策略：
  - vLLM AWQ INT4 (默认 70%)：低成本、低延迟，处理常规选品请求
  - vLLM FP16 Merged (20%)：高质量回退，当 AWQ 置信度不足或任务复杂时
  - DeepSeek V4 API (10%)：复杂多步推理、长上下文、兜底

灰度切换机制：
  - 通过环境变量 MODEL_ROUTE_WEIGHTS 动态调整比例
  - 通过特征规则（prompt 长度、是否包含 "对比"/"分析"/"预测" 等关键词）做规则二次分流
"""

import json
import os
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class RouteDecision:
    backend: str
    reason: str
    weight: float


class GrayscaleRouter:
    """灰度路由器：按配置权重 + 规则做后端选择。"""

    DEFAULT_WEIGHTS = {
        "vllm_awq": 0.70,
        "vllm_fp16": 0.20,
        "deepseek_v4": 0.10,
    }

    def __init__(self, weights: Optional[dict] = None):
        self.weights = weights or self._load_weights()
        self._validate_weights()

    @staticmethod
    def _load_weights() -> dict:
        """从环境变量或默认值加载权重。"""
        env = os.getenv("MODEL_ROUTE_WEIGHTS")
        if env:
            return json.loads(env)
        return GrayscaleRouter.DEFAULT_WEIGHTS.copy()

    def _validate_weights(self):
        total = sum(self.weights.values())
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"Route weights must sum to 1.0, got {total}")

    @staticmethod
    def _complexity_score(prompt: str) -> int:
        """根据关键词评估任务复杂度（0-100）。"""
        score = 0
        p = prompt.lower()
        complex_keywords = ["对比", "预测", "分析", "多维度", "深度", "综合", "供应链", "利润率", "风险"]
        for kw in complex_keywords:
            if kw in p:
                score += 15
        # 长文本更复杂
        score += min(len(p) // 50, 30)
        return min(score, 100)

    def route(self, prompt: str, fallback: bool = False) -> RouteDecision:
        """选择推理后端。"""
        complexity = self._complexity_score(prompt)

        # 规则优先：高复杂度直接走 DeepSeek
        if complexity >= 80:
            return RouteDecision("deepseek_v4", f"complexity={complexity}", self.weights["deepseek_v4"])

        # 命中 fallback 场景
        if fallback:
            return RouteDecision("vllm_fp16", "fallback_flag", self.weights["vllm_fp16"])

        # 按权重随机选择
        r = random.random()
        cumulative = 0.0
        for backend, weight in self.weights.items():
            cumulative += weight
            if r <= cumulative:
                reason = "weight_random"
                if backend == "deepseek_v4":
                    reason += f", complexity={complexity}"
                return RouteDecision(backend, reason, weight)

        # 兜底
        return RouteDecision("vllm_awq", "default", self.weights["vllm_awq"])

    def report(self, prompts: list[str]) -> dict:
        """对一组 prompt 进行路由统计，用于灰度效果验证。"""
        counts = {"vllm_awq": 0, "vllm_fp16": 0, "deepseek_v4": 0}
        for p in prompts:
            decision = self.route(p)
            counts[decision.backend] += 1
        total = len(prompts)
        return {
            "total": total,
            "distribution": {k: {"count": v, "ratio": round(v / total, 4)} for k, v in counts.items()},
            "weights": self.weights,
        }


def demo():
    """灰度路由演示：对真实选品 prompt 进行分流统计。"""
    prompts = [
        "请分析跨境电商平台 dog chew toys 类目的市场机会、竞品卖点与主要风险。",
        "对比 yoga mat 在亚马逊美国站的价格带、评论痛点与供应链集中度。",
        "评估 portable blender 在 TikTok Shop 的爆款潜力，给出定价与卖点建议。",
        "分析 cat water fountain 的季节性趋势、退货原因与头部供应商分布。",
        "请为 camping tent 制定选品决策：是否值得入场？目标利润率与风险点是什么？",
    ]

    router = GrayscaleRouter()
    report = router.report(prompts * 20)  # 100 条样本
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    demo()
