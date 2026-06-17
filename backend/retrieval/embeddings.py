import hashlib
from typing import Iterable


class EmbeddingService:
    def __init__(self, model_name: str = "sentence-transformers/multilingual-e5-large") -> None:
        self.model_name = model_name
        self._model = None
        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(model_name)
        except Exception:
            self._model = None

    def embed(self, texts: Iterable[str]) -> list[list[float]]:
        texts = list(texts)
        if not texts:
            return []
        if self._model is not None:
            vectors = self._model.encode(texts, normalize_embeddings=True)
            return vectors.tolist()

        results = []
        for text in texts:
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            vec = [b / 255.0 for b in digest[:32]]
            results.append(vec)
        return results
