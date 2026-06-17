import hashlib
import json
from pathlib import Path
from typing import Any

from backend.config import get_settings
from backend.rag.embeddings import EmbeddingService
from backend.rag.vector_store import FaissVectorStore
from backend.utils.helpers import is_text_file

SKIP_DIRS = {".git", ".idea", ".venv", "__pycache__", "node_modules", ".faiss", ".cache", "dist", "build"}


def build_or_load_index(repo_path: str, force_rebuild: bool = False) -> dict[str, Any]:
    repo = Path(repo_path).resolve()
    persist_dir = repo / get_settings().vector_store_dir
    store = FaissVectorStore(str(persist_dir))

    if not force_rebuild:
        try:
            if store.load():
                return {"status": "loaded", "chunks": len(store.records), "index_dir": str(persist_dir)}
        except Exception:
            pass

    documents = _collect_documents(repo)
    embeddings = EmbeddingService()
    vectors = embeddings.embed([doc["content"] for doc in documents])
    try:
        store.build(documents, vectors)
        store.save()
        status = "built"
    except Exception as exc:
        metadata_path = persist_dir / "metadata.json"
        payload = [{"record": doc, "vector": vector} for doc, vector in zip(documents, vectors)]
        metadata_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        status = f"metadata_only: {exc}"

    return {"status": status, "chunks": len(documents), "index_dir": str(persist_dir)}


def _collect_documents(repo: Path) -> list[dict[str, Any]]:
    documents: list[dict[str, Any]] = []
    for path in repo.rglob("*"):
        if _should_skip(path, repo) or not path.is_file() or not is_text_file(path):
            continue

        text = path.read_text(encoding="utf-8", errors="ignore")
        for chunk_no, chunk in enumerate(_split_chunks(text)):
            if not chunk.strip():
                continue
            start_line = chunk_no * 40 + 1
            rel_path = path.relative_to(repo).as_posix()
            documents.append(
                {
                    "id": _stable_id(rel_path, chunk_no, chunk),
                    "path": str(path),
                    "relative_path": rel_path,
                    "line": start_line,
                    "content": chunk,
                }
            )
    return documents


def _split_chunks(content: str, max_lines: int = 40, overlap: int = 8) -> list[str]:
    lines = content.splitlines()
    if not lines:
        return []

    chunks = []
    step = max_lines - overlap
    for start in range(0, len(lines), step):
        chunks.append("\n".join(lines[start : start + max_lines]))
    return chunks


def _should_skip(path: Path, repo: Path) -> bool:
    try:
        rel_parts = path.relative_to(repo).parts
    except ValueError:
        return True
    return any(part in SKIP_DIRS for part in rel_parts)


def _stable_id(relative_path: str, chunk_no: int, chunk: str) -> str:
    digest = hashlib.sha1(f"{relative_path}:{chunk_no}:{chunk}".encode("utf-8")).hexdigest()[:12]
    return f"{relative_path}:{chunk_no}:{digest}"
