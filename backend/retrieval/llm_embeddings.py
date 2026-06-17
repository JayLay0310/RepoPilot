import os
import json
from typing import List, Dict, Any, Optional
from pathlib import Path

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

from backend.config import get_settings


class CodeEmbeddings:
    """代码片段向量化处理"""

    def __init__(self, model_name: str = "sentence-transformers/multilingual-e5-large"):
        self.model_name = model_name
        self.model = None
        self.embeddings_cache: Dict[str, List[float]] = {}
        self._init_model()

    def _init_model(self):
        """初始化向量模型"""
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            print(f"Warning: sentence-transformers not available")
            return

        try:
            self.model = SentenceTransformer(self.model_name)
        except Exception as e:
            print(f"Error loading model {self.model_name}: {e}")

    def embed(self, text: str, use_cache: bool = True) -> Optional[List[float]]:
        """将文本转换为向量"""
        if self.model is None:
            return None

        # 使用缓存
        if use_cache and text in self.embeddings_cache:
            return self.embeddings_cache[text]

        try:
            embedding = self.model.encode(text, convert_to_numpy=True)
            result = embedding.tolist() if NUMPY_AVAILABLE else embedding
            
            if use_cache:
                self.embeddings_cache[text] = result
            
            return result
        except Exception as e:
            print(f"Error embedding text: {e}")
            return None

    def embed_batch(self, texts: List[str], use_cache: bool = True) -> List[Optional[List[float]]]:
        """批量将文本转换为向量"""
        if self.model is None:
            return [None] * len(texts)

        # 分离缓存中有的和没有的
        to_embed = []
        to_embed_indices = []
        results = [None] * len(texts)

        for i, text in enumerate(texts):
            if use_cache and text in self.embeddings_cache:
                results[i] = self.embeddings_cache[text]
            else:
                to_embed.append(text)
                to_embed_indices.append(i)

        if to_embed:
            try:
                embeddings = self.model.encode(to_embed, convert_to_numpy=True)
                for idx, emb_idx in enumerate(to_embed_indices):
                    result = embeddings[idx].tolist() if NUMPY_AVAILABLE else embeddings[idx]
                    results[emb_idx] = result
                    
                    if use_cache:
                        self.embeddings_cache[to_embed[idx]] = result
            except Exception as e:
                print(f"Error batch embedding: {e}")

        return results

    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算两个向量的余弦相似度"""
        if not NUMPY_AVAILABLE:
            return 0.0
        
        try:
            arr1 = np.array(vec1)
            arr2 = np.array(vec2)
            return float(np.dot(arr1, arr2) / (np.linalg.norm(arr1) * np.linalg.norm(arr2)))
        except Exception as e:
            print(f"Error computing similarity: {e}")
            return 0.0

    def save_cache(self, path: str) -> bool:
        """保存向量缓存"""
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w") as f:
                json.dump(self.embeddings_cache, f)
            return True
        except Exception as e:
            print(f"Error saving cache: {e}")
            return False

    def load_cache(self, path: str) -> bool:
        """加载向量缓存"""
        try:
            if Path(path).exists():
                with open(path, "r") as f:
                    self.embeddings_cache = json.load(f)
                return True
        except Exception as e:
            print(f"Error loading cache: {e}")
        return False


def get_embeddings() -> CodeEmbeddings:
    """获取向量化处理实例"""
    settings = get_settings()
    return CodeEmbeddings(model_name=settings.embedding_model)
