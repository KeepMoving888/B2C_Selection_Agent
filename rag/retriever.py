# ============================================================
# rag/retriever.py — 历史报告 + 领域知识检索器
#
# 职责：
#   1. 构建并维护可检索知识库（历史选品报告 + 领域微调数据）
#   2. 接收用户查询，返回最相关的 top-k 上下文片段
#   3. 暴露检索耗时与命中数给 MetricsCollector
# ============================================================

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Dict, List, Optional

from rag.store import VectorStore, load_domain_knowledge, load_report_documents

if TYPE_CHECKING:
    from monitoring.metrics import MetricsCollector


class ReportRetriever:
    """
    历史报告与领域知识检索器。

    用法：
        retriever = ReportRetriever()
        retriever.build_index()                          # 一次性建索引
        ctx = retriever.retrieve("分析宠物咀嚼玩具在美国的市场")  # 返回格式化上下文
    """

    def __init__(
        self,
        output_dir: str = "./output",
        data_dir: str = "./finetune/data",
        store: Optional[VectorStore] = None,
        metrics_collector: Optional["MetricsCollector"] = None,
    ):
        self.output_dir = output_dir
        self.data_dir = data_dir
        self.store = store or VectorStore(collection_name="reports")
        self._metrics = metrics_collector

    def build_index(self, include_reports: bool = True, include_domain: bool = True):
        """加载本地报告与领域知识并写入向量/内存索引"""
        docs = []
        if include_reports:
            docs.extend(load_report_documents(self.output_dir))
        if include_domain:
            docs.extend(load_domain_knowledge(self.data_dir))
        self.store.add_documents(docs)
        return len(docs)

    def retrieve(self, query: str, top_k: int = 3) -> Dict:
        """
        检索与查询最相关的上下文。

        返回：
            {
                "query": query,
                "hits": [...],
                "context": "格式化后的上下文文本",
                "hit_count": int,
                "elapsed_seconds": float,
            }
        """
        start = time.time()
        try:
            hits = self.store.search(query, top_k=top_k)
            success = True
        except Exception as e:
            hits = []
            success = False
            if self._metrics:
                self._metrics.record_rag_query(
                    duration_seconds=time.time() - start,
                    hits=0,
                    success=False,
                )
            raise

        elapsed = time.time() - start
        if self._metrics:
            self._metrics.record_rag_query(
                duration_seconds=elapsed,
                hits=len(hits),
                success=success,
            )

        context = self._format_context(hits)
        return {
            "query": query,
            "hits": hits,
            "context": context,
            "hit_count": len(hits),
            "elapsed_seconds": elapsed,
        }

    def _format_context(self, hits: List[Dict]) -> str:
        """将检索结果格式化为可供 LLM 使用的上下文文本"""
        if not hits:
            return ""
        parts = ["### 相关历史报告与领域知识参考"]
        for i, hit in enumerate(hits, 1):
            meta = hit.get("metadata", {})
            source = meta.get("filename") or meta.get("source", "unknown")
            score = hit.get("score", 0.0)
            text = hit.get("text", "").strip()
            if not text:
                continue
            parts.append(f"\n[参考 {i}] 来源: {source} | 相关度: {score:.2f}\n{text}")
        return "\n".join(parts)

    def clear(self):
        self.store.clear()
