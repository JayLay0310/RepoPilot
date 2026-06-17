import hashlib
from typing import Iterable

from backend.config import get_settings


class EmbeddingService:
    """Small wrapper around sentence-transformers with a deterministic fallback."""

    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or get_settings().embedding_model
        self._model = None
        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name, local_files_only=True)
        except Exception:
            self._model = None

    @property
    def dimension(self) -> int:
        if self._model is not None:
            return int(self._model.get_sentence_embedding_dimension())
        return 384

    def embed(self, texts: Iterable[str]) -> list[list[float]]:
        texts = list(texts)
        if not texts:
            return []

        if self._model is not None:
            vectors = self._model.encode(texts, normalize_embeddings=True)
            return vectors.tolist()

        return [self._fallback_embedding(text) for text in texts]

    def _fallback_embedding(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        tokens = text.lower().split()
        if not tokens:
            tokens = [text.lower()]

        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            for idx, value in enumerate(digest):
                vector[idx % self.dimension] += (value / 255.0) - 0.5

        norm = sum(value * value for value in vector) ** 0.5 or 1.0
        return [value / norm for value in vector]
