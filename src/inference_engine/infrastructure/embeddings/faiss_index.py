from typing import List, Dict, Any
import numpy as np

try:
    import faiss  # type: ignore
except Exception:  # pragma: no cover
    faiss = None  # type: ignore


class InMemoryVectorStore:
    def __init__(self, dim: int):
        self.dim = dim
        self.embeddings: Dict[str, np.ndarray] = {}
        self.metadata: Dict[str, Dict[str, Any]] = {}

    async def add(self, id: str, embedding: np.ndarray, metadata: Dict[str, Any]) -> None:
        self.embeddings[id] = embedding.astype(np.float32)
        self.metadata[id] = metadata

    async def search(self, query_embedding: np.ndarray, top_k: int, max_distance: float) -> List[Dict[str, Any]]:
        if not self.embeddings:
            return []
        q = query_embedding.astype(np.float32)
        results: List[Dict[str, Any]] = []
        for k, v in self.embeddings.items():
            # cosine distance using dot since assume normalized
            sim = float(np.dot(q, v))
            distance = 1.0 - sim
            if distance <= max_distance:
                results.append({"id": k, "distance": distance, **self.metadata.get(k, {})})
        results.sort(key=lambda r: r["distance"])  # ascending distance
        return results[:top_k]

    async def delete(self, id: str) -> None:
        self.embeddings.pop(id, None)
        self.metadata.pop(id, None)

    async def clear(self) -> None:
        self.embeddings.clear()
        self.metadata.clear()
