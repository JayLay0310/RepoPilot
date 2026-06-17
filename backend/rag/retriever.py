import json
from pathlib import Path
from typing import Any

from backend.config import get_settings
from backend.rag.embeddings import EmbeddingService
from backend.rag.indexer import build_or_load_index
from backend.rag.vector_store import FaissVectorStore
from backend.tools.code_search import keyword_search


def semantic_retrieve(repo_path: str, query: str, top_k: int = 10) -> list[dict[str, Any]]:
    build_or_load_index(repo_path)
    repo = Path(repo_path).resolve()
    persist_dir = repo / get_settings().vector_store_dir
    embeddings = EmbeddingService()
    query_vector = embeddings.embed([query])[0]

    store = FaissVectorStore(str(persist_dir))
    try:
        if store.load():
            return store.search(query_vector, top_k=top_k)
    except Exception:
        return _metadata_search(persist_dir, query_vector, top_k)
    return []


def hybrid_retrieve(repo_path: str, query: str, top_k: int = 10, keyword_top_k: int = 20) -> list[dict[str, Any]]:
    semantic = semantic_retrieve(repo_path, query, top_k=top_k)
    keyword = [
        {**item, "score": 0.35, "source": "keyword"}
        for item in keyword_search(repo_path, query, top_k=keyword_top_k)
    ]
    return _merge_results(semantic, keyword, top_k)


def _metadata_search(persist_dir: Path, query_vector: list[float], top_k: int) -> list[dict[str, Any]]:
    metadata_path = persist_dir / "metadata.json"
    if not metadata_path.exists():
        return []

    payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    scored = []
    for item in payload:
        record = dict(item["record"])
        score = _cosine(query_vector, item["vector"])
        record["score"] = score
        record["source"] = "metadata"
        scored.append(record)
    scored.sort(key=lambda row: row["score"], reverse=True)
    return scored[:top_k]


def _merge_results(semantic: list[dict[str, Any]], keyword: list[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
    merged: dict[tuple[str, int, str], dict[str, Any]] = {}
    for item in semantic + keyword:
        key = (item.get("path", ""), int(item.get("line", 0) or 0), item.get("content", "")[:120])
        if key not in merged or float(item.get("score", 0)) > float(merged[key].get("score", 0)):
            merged[key] = item

    return sorted(merged.values(), key=lambda row: float(row.get("score", 0)), reverse=True)[:top_k]


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5 or 1.0
    norm_b = sum(y * y for y in b) ** 0.5 or 1.0
    return dot / (norm_a * norm_b)
