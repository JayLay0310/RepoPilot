from typing import List, Dict, Any
from pathlib import Path

try:
    from rank_bm25 import BM25Okapi
    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False

from backend.retrieval.llm_embeddings import CodeEmbeddings
from backend.tools.code_search import keyword_search


class HybridRetriever:
    """混合检索：结合 BM25 关键词和向量语义相似度"""

    def __init__(self, embeddings: CodeEmbeddings, repo_path: str):
        self.embeddings = embeddings
        self.repo_path = repo_path
        self.bm25 = None
        self.documents = []
        self.metadata = []

    def build_index(self, documents: List[Dict[str, Any]]) -> bool:
        """构建检索索引
        
        Args:
            documents: 文档列表，每个文档应包含:
                {"id": str, "content": str, "path": str, "line": int}
        """
        if not documents:
            return False

        self.documents = documents
        self.metadata = [{"id": d["id"], "path": d["path"], "line": d.get("line", 0)} for d in documents]

        # 构建 BM25 索引
        if BM25_AVAILABLE:
            try:
                texts = [d["content"] for d in documents]
                tokenized_docs = [text.split() for text in texts]
                self.bm25 = BM25Okapi(tokenized_docs)
                return True
            except Exception as e:
                print(f"Error building BM25 index: {e}")
                self.bm25 = None
        
        return True

    def search(
        self,
        query: str,
        top_k: int = 10,
        alpha: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """混合检索
        
        Args:
            query: 查询文本
            top_k: 返回的前K个结果
            alpha: BM25 权重 (0-1)，1-alpha 是向量相似度权重
        
        Returns:
            包含 {"id", "path", "line", "content", "score"} 的结果列表
        """
        results = []
        scores = {}

        # BM25 关键词搜索
        if self.bm25 is not None:
            try:
                tokenized_query = query.split()
                bm25_scores = self.bm25.get_scores(tokenized_query)
                for i, score in enumerate(bm25_scores):
                    if score > 0:
                        scores[i] = scores.get(i, 0) + alpha * score
            except Exception as e:
                print(f"Error in BM25 search: {e}")

        # 向量语义搜索
        if self.embeddings.model is not None:
            try:
                query_embedding = self.embeddings.embed(query)
                if query_embedding:
                    for i, doc in enumerate(self.documents):
                        doc_embedding = self.embeddings.embed(doc["content"])
                        if doc_embedding:
                            similarity = self.embeddings.cosine_similarity(
                                query_embedding, doc_embedding
                            )
                            scores[i] = scores.get(i, 0) + (1 - alpha) * similarity
            except Exception as e:
                print(f"Error in vector search: {e}")

        # 排序并返回
        sorted_indices = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        
        for idx, score in sorted_indices:
            doc = self.documents[idx]
            meta = self.metadata[idx]
            results.append({
                "id": meta["id"],
                "path": meta["path"],
                "line": meta["line"],
                "content": doc["content"][:200],  # 返回前200个字符
                "score": score,
            })

        return results

    def simple_search(
        self,
        query: str,
        repo_path: str,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """简单检索：直接使用关键词搜索（不依赖索引）"""
        return keyword_search(repo_path, query, top_k=top_k)
