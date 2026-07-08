# ============================================================
# rag/store.py — 文档存储与检索抽象
#
# 设计：
#   - 优先使用 ChromaDB + sentence-transformers（生产环境）
#   - 未安装时自动降级为纯 Python 内存索引（TF 余弦相似度）
#   - 统一接口：add_document / search / clear
# ============================================================

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Dict, List, Optional


class Document:
    """存储的最小文档单元"""

    def __init__(self, doc_id: str, text: str, metadata: Optional[Dict] = None):
        self.doc_id = doc_id
        self.text = text
        self.metadata = metadata or {}


class _TokenIndex:
    """纯 Python 内存索引：基于词频的余弦相似度检索。"""

    _WORD_RE = re.compile(r"[a-zA-Z0-9_]+")
    _CJK_RE = re.compile(r"[\u4e00-\u9fa5]")

    def __init__(self):
        self._docs: Dict[str, Document] = {}
        self._doc_tokens: Dict[str, Dict[str, float]] = {}
        self._idf: Dict[str, float] = {}
        self._dirty = False

    @classmethod
    def _tokenize(cls, text: str) -> List[str]:
        """英文按单词、CJK 按单字分词，兼顾中英文混合场景"""
        tokens = []
        lowered = text.lower()
        # 英文/数字词
        tokens.extend(cls._WORD_RE.findall(lowered))
        # CJK 单字（避免未分词导致的长词无法匹配）
        tokens.extend(cls._CJK_RE.findall(lowered))
        return tokens

    @classmethod
    def _term_freq(cls, tokens: List[str]) -> Dict[str, float]:
        freq: Dict[str, int] = {}
        for t in tokens:
            freq[t] = freq.get(t, 0) + 1
        total = len(tokens) or 1
        return {t: c / total for t, c in freq.items()}

    def _rebuild_idf(self):
        if not self._dirty:
            return
        doc_count = len(self._docs) or 1
        df: Dict[str, int] = {}
        for terms in self._doc_tokens.values():
            for t in terms:
                df[t] = df.get(t, 0) + 1
        self._idf = {t: math.log((doc_count + 1) / (df[t] + 1)) for t in df}
        self._dirty = False

    def add(self, doc: Document):
        self._docs[doc.doc_id] = doc
        self._doc_tokens[doc.doc_id] = self._term_freq(
            self._tokenize(doc.text))
        self._dirty = True

    def search(self, query: str, top_k: int = 3) -> List[Dict]:
        self._rebuild_idf()
        q_tokens = self._tokenize(query)
        q_terms = self._term_freq(q_tokens)
        q_vec = {t: v * self._idf.get(t, 0.0) for t, v in q_terms.items()}
        q_norm = math.sqrt(sum(v * v for v in q_vec.values())) or 1.0

        scores: List[tuple] = []
        for doc_id, terms in self._doc_tokens.items():
            doc_vec = {t: v * self._idf.get(t, 0.0) for t, v in terms.items()}
            dot = sum(q_vec.get(t, 0.0) * doc_vec.get(t, 0.0) for t in q_vec)
            d_norm = math.sqrt(sum(v * v for v in doc_vec.values())) or 1.0
            score = dot / (q_norm * d_norm)
            scores.append((doc_id, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        results = []
        for doc_id, score in scores[:top_k]:
            if score <= 0:
                continue
            doc = self._docs[doc_id]
            results.append({
                "id": doc_id,
                "text": doc.text,
                "score": round(score, 4),
                "metadata": doc.metadata,
            })
        return results

    def clear(self):
        self._docs.clear()
        self._doc_tokens.clear()
        self._idf.clear()
        self._dirty = False


class VectorStore:
    """
    向量存储统一入口。

    优先尝试 ChromaDB + sentence-transformers；缺失时自动降级为内存索引。
    """

    def __init__(self, collection_name: str = "reports"):
        self.collection_name = collection_name
        self._chroma = None
        self._embedding_fn = None
        self._fallback: Optional[_TokenIndex] = None

        try:
            import chromadb
            from chromadb.config import Settings
            from sentence_transformers import SentenceTransformer

            client = chromadb.Client(
                Settings(
                    chroma_db_impl="duckdb+parquet",
                    persist_directory="./chroma_db",
                )
            )
            self._chroma = client.get_or_create_collection(name=collection_name)
            # 使用轻量双语模型；未下载时会自动下载
            self._embedding_fn = SentenceTransformer("BAAI/bge-small-zh-v1.5")
        except Exception:
            # 降级为内存索引
            self._fallback = _TokenIndex()

    def is_fallback(self) -> bool:
        return self._fallback is not None

    def add_document(self, doc_id: str, text: str, metadata: Optional[Dict] = None):
        metadata = metadata or {}
        if self._chroma is not None:
            try:
                self._chroma.add(
                    ids=[doc_id],
                    documents=[text],
                    metadatas=[metadata],
                )
                return
            except Exception:
                # 写入失败时降级
                if self._fallback is None:
                    self._fallback = _TokenIndex()
        self._fallback.add(Document(doc_id, text, metadata))

    def add_documents(self, docs: List[Document]):
        for doc in docs:
            self.add_document(doc.doc_id, doc.text, doc.metadata)

    def search(self, query: str, top_k: int = 3) -> List[Dict]:
        if self._chroma is not None and self._embedding_fn is not None:
            try:
                query_embedding = self._embedding_fn.encode(query).tolist()
                results = self._chroma.query(
                    query_embeddings=[query_embedding],
                    n_results=top_k,
                    include=["documents", "metadatas", "distances"],
                )
                items = []
                for i, doc_id in enumerate(results.get("ids", [[]])[0]):
                    items.append({
                        "id": doc_id,
                        "text": results["documents"][0][i],
                        "score": 1.0 - float(results["distances"][0][i]),
                        "metadata": results["metadatas"][0][i],
                    })
                return items
            except Exception:
                if self._fallback is None:
                    self._fallback = _TokenIndex()
        return self._fallback.search(query, top_k)

    def clear(self):
        if self._chroma is not None:
            try:
                self._chroma.delete(where={"$exists": True})
            except Exception:
                pass
        if self._fallback is not None:
            self._fallback.clear()

    def count(self) -> int:
        if self._chroma is not None:
            try:
                return self._chroma.count()
            except Exception:
                pass
        return len(self._fallback._docs) if self._fallback else 0


def load_report_documents(output_dir: str = "./output") -> List[Document]:
    """从 output 目录加载历史报告 JSON 文件为文档"""
    docs: List[Document] = []
    path = Path(output_dir)
    if not path.exists():
        return docs

    for fp in sorted(path.glob("*.json")):
        try:
            import json
            data = json.loads(fp.read_text(encoding="utf-8"))
            # 抽取可检索文本
            text_parts = []
            if isinstance(data, dict):
                text_parts.append(data.get("executive_summary", ""))
                text_parts.append(data.get("product_name", ""))
                text_parts.append(data.get("market", ""))
                text_parts.append(data.get("platform", ""))
                detailed = data.get("detailed_analysis", {})
                if isinstance(detailed, dict):
                    text_parts.append(" ".join(str(v) for v in detailed.values()))
            text = "\n".join(p for p in text_parts if p)
            if not text:
                continue
            docs.append(Document(
                doc_id=f"report:{fp.stem}",
                text=text,
                metadata={
                    "source": str(fp),
                    "type": "historical_report",
                    "filename": fp.name,
                },
            ))
        except Exception:
            continue
    return docs


def load_domain_knowledge(data_dir: str = "./finetune/data") -> List[Document]:
    """加载领域知识（微调数据中的 chosen_response）作为检索源"""
    docs: List[Document] = []
    path = Path(data_dir)
    if not path.exists():
        return docs

    orpo_file = path / "orpo_chosen_rejected.jsonl"
    if orpo_file.exists():
        try:
            import json
            for i, line in enumerate(orpo_file.read_text(encoding="utf-8").splitlines()):
                if not line.strip():
                    continue
                obj = json.loads(line)
                text = f"{obj.get('prompt', '')}\n{obj.get('chosen', '')}"
                docs.append(Document(
                    doc_id=f"domain:orpo:{i}",
                    text=text,
                    metadata={"type": "domain_knowledge", "source": str(orpo_file)},
                ))
        except Exception:
            pass

    sft_file = path / "sft_train.jsonl"
    if sft_file.exists():
        try:
            import json
            for i, line in enumerate(sft_file.read_text(encoding="utf-8").splitlines()):
                if not line.strip():
                    continue
                obj = json.loads(line)
                messages = obj.get("messages", [])
                text = "\n".join(m.get("content", "") for m in messages[-2:])
                docs.append(Document(
                    doc_id=f"domain:sft:{i}",
                    text=text,
                    metadata={"type": "domain_knowledge", "source": str(sft_file)},
                ))
        except Exception:
            pass

    return docs
