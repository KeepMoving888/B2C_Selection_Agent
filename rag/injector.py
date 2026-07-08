# ============================================================
# rag/injector.py — RAG 上下文注入器
#
# 职责：
#   在 AgentLoop 的 Understand / Plan 阶段前，把检索到的历史报告
#   和领域知识注入到 prompt 中，提升分析质量与一致性。
# ============================================================

from __future__ import annotations

from typing import Dict, Optional

from rag.retriever import ReportRetriever


class ContextInjector:
    """
    RAG 上下文注入器。

    支持两种注入模式：
      - prepend: 将检索上下文拼接在用户 prompt 前面
      - system:  将检索上下文作为 system message 追加
    """

    def __init__(
        self,
        retriever: ReportRetriever,
        mode: str = "prepend",
        top_k: int = 3,
        max_context_chars: int = 3000,
    ):
        self.retriever = retriever
        self.mode = mode
        self.top_k = top_k
        self.max_context_chars = max_context_chars

    def inject(self, prompt: str, query: Optional[str] = None) -> str:
        """将检索上下文注入 prompt"""
        q = query or prompt
        result = self.retriever.retrieve(q, top_k=self.top_k)
        context = result.get("context", "")
        if not context:
            return prompt

        context = context[:self.max_context_chars]
        if self.mode == "prepend":
            return f"{context}\n\n---\n\n用户请求：\n{prompt}"
        if self.mode == "system":
            return (
                "系统补充信息（仅作参考，请结合当前请求分析）：\n"
                f"{context}\n\n用户请求：\n{prompt}"
            )
        return prompt

    def inject_context_dict(
        self,
        task: str,
        context: Dict,
    ) -> Dict:
        """
        向 ExecutionContext 注入检索结果摘要。
        AgentLoop 可在 _understand 前调用此方法预热知识库。
        """
        result = self.retriever.retrieve(task, top_k=self.top_k)
        if result.get("context"):
            context["retrieved_knowledge"] = result["context"]
            context["retrieved_hit_count"] = result.get("hit_count", 0)
        return context
