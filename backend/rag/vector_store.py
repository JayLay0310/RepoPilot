import json
from pathlib import Path
from typing import Any

import numpy as np


class FaissVectorStore:
    def __init__(self, persist_dir: str) -> None:
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.records: list[dict[str, Any]] = []
        self.index = None

    @property
    def index_path(self) -> Path:
        return self.persist_dir / "index.faiss"

    @property
    def metadata_path(self) -> Path:
        return self.persist_dir / "metadata.json"

    def build(self, records: list[dict[str, Any]], vectors: list[list[float]]) -> None:
        if not records or not vectors:
            self.records = []
            self.index = None
            return

        import faiss

        matrix = np.asarray(vectors, dtype="float32")
        faiss.normalize_L2(matrix)
        self.index = faiss.IndexFlatIP(matrix.shape[1])
        self.index.add(matrix)
        self.records = records

    def save(self) -> None:
        if self.index is None:
            return

        import faiss

        faiss.write_index(self.index, str(self.index_path))
        self.metadata_path.write_text(json.dumps(self.records, ensure_ascii=False, indent=2), encoding="utf-8")

    def load(self) -> bool:
        if not self.index_path.exists() or not self.metadata_path.exists():
            return False

        import faiss

        self.index = faiss.read_index(str(self.index_path))
        self.records = json.loads(self.metadata_path.read_text(encoding="utf-8"))
        return True

    def search(self, query_vector: list[float], top_k: int) -> list[dict[str, Any]]:
        if self.index is None or not self.records:
            return []

        vector = np.asarray([query_vector], dtype="float32")
        import faiss

        faiss.normalize_L2(vector)
        scores, indices = self.index.search(vector, min(top_k, len(self.records)))
        results: list[dict[str, Any]] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue
            item = dict(self.records[int(idx)])
            item["score"] = float(score)
            item["source"] = "faiss"
            results.append(item)
        return results
