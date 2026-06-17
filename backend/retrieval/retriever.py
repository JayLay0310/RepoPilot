from collections import defaultdict

from backend.retrieval.embeddings import EmbeddingService
from backend.retrieval.vector_store import VectorStore


class HybridRetriever:
    def __init__(self, embedding_service: EmbeddingService, vector_store: VectorStore) -> None:
        self.embedding_service = embedding_service
        self.vector_store = vector_store

    def retrieve(self, query: str, top_k: int = 5) -> list[dict]:
        vector = self.embedding_service.embed([query])[0]
        semantic = self.vector_store.search(vector, top_k=top_k * 2)

        keyword_scores = defaultdict(int)
        query_tokens = set(query.lower().split())
        for item in semantic:
            chunk_tokens = set(item["chunk"].lower().split())
            keyword_scores[item["id"]] = len(query_tokens & chunk_tokens)

        ranked = sorted(semantic, key=lambda x: (keyword_scores[x["id"]],), reverse=True)
        unique, seen = [], set()
        for item in ranked:
            if item["id"] not in seen:
                unique.append(item)
                seen.add(item["id"])
            if len(unique) >= top_k:
                break
        return unique
