from typing import Dict
import asyncio
import numpy as np

try:
    from sentence_transformers import SentenceTransformer
except Exception:  # pragma: no cover
    SentenceTransformer = None  # type: ignore


class EmbeddingModel:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = SentenceTransformer(model_name) if SentenceTransformer else None
        self._cache: Dict[str, np.ndarray] = {}

    async def embed(self, text: str) -> np.ndarray:
        if text in self._cache:
            return self._cache[text]
        loop = asyncio.get_running_loop()
        if self._model is None:
            # Fallback: deterministic hash-based pseudo-embedding
            vec = np.random.default_rng(abs(hash(text)) % (2**32)).random(384).astype(np.float32)
        else:
            vec = await loop.run_in_executor(None, lambda: self._model.encode(text, normalize_embeddings=True))
        self._cache[text] = vec
        return vec
