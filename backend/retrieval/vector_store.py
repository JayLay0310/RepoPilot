import json
from math import sqrt
from pathlib import Path


class VectorStore:
    def __init__(self, persist_dir: str = ".faiss") -> None:
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.records: list[dict] = []

    def upsert_many(self, items: list[dict]) -> None:
        self.records.extend(items)

    def search(self, query_vector: list[float], top_k: int = 5) -> list[dict]:
        def cosine(a: list[float], b: list[float]) -> float:
            dot = sum(x * y for x, y in zip(a, b))
            na = sqrt(sum(x * x for x in a)) or 1.0
            nb = sqrt(sum(y * y for y in b)) or 1.0
            return dot / (na * nb)

        scored = []
        for item in self.records:
            score = cosine(query_vector, item["vector"])
            scored.append((score, item))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [i for _, i in scored[:top_k]]

    def persist(self) -> None:
        payload = [{k: v for k, v in item.items()} for item in self.records]
        (self.persist_dir / "vectors.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def load(self) -> None:
        file_path = self.persist_dir / "vectors.json"
        if file_path.exists():
            self.records = json.loads(file_path.read_text(encoding="utf-8"))
