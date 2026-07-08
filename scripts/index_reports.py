#!/usr/bin/env python3
# ============================================================
# scripts/index_reports.py — 历史报告与领域知识建索引
#
# 用法：
#   python scripts/index_reports.py
#
# 说明：
#   扫描 output/ 下的历史报告与 finetune/data/ 下的领域数据，
#   写入向量存储（ChromaDB 或内存索引），供 Agentic RAG 检索使用。
# ============================================================

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from rag.retriever import ReportRetriever


def main():
    output_dir = os.environ.get("OUTPUT_DIR", "./output")
    data_dir = os.environ.get("FINETUNE_DATA_DIR", "./finetune/data")

    retriever = ReportRetriever(
        output_dir=output_dir,
        data_dir=data_dir,
    )
    print(f"[RAG] Building index from {output_dir} and {data_dir} ...")
    count = retriever.build_index(
        include_reports=True,
        include_domain=True,
    )
    print(f"[RAG] Indexed {count} documents")
    print(f"[RAG] Backend: {'fallback' if retriever.store.is_fallback() else 'chroma'}")
    print(f"[RAG] Total indexed docs: {retriever.store.count()}")

    # 示例检索
    demo_query = "分析宠物咀嚼玩具在美国亚马逊的市场"
    print(f"\n[RAG] Demo query: {demo_query}")
    result = retriever.retrieve(demo_query, top_k=3)
    print(f"[RAG] Hits: {result['hit_count']} | Elapsed: {result['elapsed_seconds']:.3f}s")
    for hit in result["hits"]:
        print(f"  - {hit['id']} (score={hit['score']})")


if __name__ == "__main__":
    main()
