from pathlib import Path

from backend.retrieval.embeddings import EmbeddingService
from backend.retrieval.vector_store import VectorStore
from backend.utils.helpers import is_text_file


class CodeIndexer:
    def __init__(self, embedding_service: EmbeddingService, vector_store: VectorStore) -> None:
        self.embedding_service = embedding_service
        self.vector_store = vector_store

    def index_repo(self, repo_path: str) -> int:
        repo = Path(repo_path)
        chunks = []
        for path in repo.rglob("*"):
            if path.is_file() and is_text_file(path):
                text = path.read_text(encoding="utf-8", errors="ignore")
                for idx, chunk in enumerate(self._split_chunks(text)):
                    chunks.append({"id": f"{path}:{idx}", "path": str(path), "chunk": chunk})

        vectors = self.embedding_service.embed([c["chunk"] for c in chunks])
        items = []
        for chunk, vector in zip(chunks, vectors):
            chunk["vector"] = vector
            items.append(chunk)
        self.vector_store.upsert_many(items)
        return len(items)

    @staticmethod
    def _split_chunks(content: str, max_lines: int = 30) -> list[str]:
        lines = content.splitlines()
        return ["\n".join(lines[i : i + max_lines]) for i in range(0, len(lines), max_lines)] or [""]
