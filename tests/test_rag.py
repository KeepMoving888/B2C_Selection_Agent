# ============================================================
# tests/test_rag.py — Agentic RAG 检索层测试
# ============================================================

import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, '.')

from rag.injector import ContextInjector
from rag.retriever import ReportRetriever
from rag.store import (
    Document,
    VectorStore,
    load_domain_knowledge,
    load_report_documents,
)


class _FakeStore:
    """用于测试 ReportRetriever 的内存 Store 替代"""

    def __init__(self):
        self.docs = []

    def is_fallback(self):
        return True

    def add_document(self, doc_id: str, text: str, metadata=None):
        self.docs.append(Document(doc_id, text, metadata or {}))

    def add_documents(self, docs):
        self.docs.extend(docs)

    def search(self, query, top_k=3):
        results = []
        for doc in self.docs[:top_k]:
            results.append({
                "id": doc.doc_id,
                "text": doc.text,
                "score": 0.9,
                "metadata": doc.metadata,
            })
        return results

    def clear(self):
        self.docs.clear()

    def count(self):
        return len(self.docs)


def test_vector_store_fallback_search():
    """VectorStore 在未安装 ChromaDB 时应使用内存索引完成检索"""
    store = VectorStore(collection_name="test_fallback")
    store.add_document("doc1", "宠物咀嚼玩具在美国亚马逊热销，毛利率高", {"type": "report"})
    store.add_document("doc2", "瑜伽裤欧洲市场竞争激烈", {"type": "report"})

    results = store.search("宠物玩具 美国", top_k=2)
    assert len(results) >= 1
    assert results[0]["id"] == "doc1"
    assert results[0]["score"] > 0


def test_report_retriever_uses_metrics():
    """ReportRetriever 应正确返回检索结果并调用 MetricsCollector"""
    store = _FakeStore()
    metrics_calls = []

    class FakeMetrics:
        def record_rag_query(self, duration_seconds, hits, success=True):
            metrics_calls.append({
                "duration_seconds": duration_seconds,
                "hits": hits,
                "success": success,
            })

    retriever = ReportRetriever(
        output_dir="./output",
        data_dir="./finetune/data",
        store=store,
        metrics_collector=FakeMetrics(),
    )
    retriever.store.add_document(
        "domain:orpo:1",
        "分析不锈钢保温杯在美国亚马逊，市场评分 82/100",
        {"type": "domain_knowledge"},
    )

    result = retriever.retrieve("不锈钢保温杯 美国亚马逊", top_k=1)
    assert result["hit_count"] == 1
    assert "不锈钢保温杯" in result["context"]
    assert len(metrics_calls) == 1
    assert metrics_calls[0]["hits"] == 1
    assert metrics_calls[0]["success"] is True


def test_context_injector_prepend_mode():
    """ContextInjector prepend 模式应将检索上下文插入 prompt 前部"""
    store = _FakeStore()
    retriever = ReportRetriever(store=store)
    retriever.store.add_document(
        "doc:x",
        "历史分析：宠物玩具美国市场评分 80/100",
        {"filename": "report_x.json"},
    )

    injector = ContextInjector(retriever, mode="prepend", top_k=1)
    prompt = "分析宠物玩具在美国的市场"
    injected = injector.inject(prompt, query=prompt)

    assert "相关历史报告与领域知识参考" in injected
    assert "宠物玩具美国市场评分 80/100" in injected
    assert prompt in injected


def test_context_injector_no_hits():
    """无命中时 injector 应原样返回 prompt"""
    store = _FakeStore()
    retriever = ReportRetriever(store=store)
    injector = ContextInjector(retriever, top_k=1)
    prompt = "分析某种不存在的产品"
    assert injector.inject(prompt) == prompt


def test_load_report_documents(tmp_path):
    """load_report_documents 应正确解析 output 目录下的 JSON 报告"""
    report = {
        "executive_summary": "硅胶折叠水杯在英国站表现良好",
        "product_name": "硅胶折叠水杯",
        "market": "UK",
        "platform": "amazon.co.uk",
        "detailed_analysis": {"competition": "中等", "margin": "35%"},
    }
    report_file = tmp_path / "report_20240101_120000.json"
    report_file.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")

    docs = load_report_documents(str(tmp_path))
    assert len(docs) == 1
    assert "硅胶折叠水杯" in docs[0].text
    assert docs[0].metadata["type"] == "historical_report"


def test_load_domain_knowledge(tmp_path):
    """load_domain_knowledge 应正确加载 ORPO/SFT 数据"""
    orpo_file = tmp_path / "orpo_chosen_rejected.jsonl"
    orpo_file.write_text(
        json.dumps({"prompt": "分析A", "chosen": "高质量回答"}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    sft_file = tmp_path / "sft_train.jsonl"
    sft_file.write_text(
        json.dumps({"messages": [{"role": "user", "content": "问"}, {"role": "assistant", "content": "答"}]}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    docs = load_domain_knowledge(str(tmp_path))
    assert len(docs) == 2
    texts = " ".join(d.text for d in docs)
    assert "高质量回答" in texts
    assert "答" in texts
