from __future__ import annotations

import abc
from typing import Optional, Tuple, Protocol, Any, List

from ..models.request import InferenceRequest
from ..models.response import InferenceResponse, CacheInfo


class VectorStore(Protocol):
    async def add(self, id: str, embedding: Any, metadata: dict) -> None: ...

    async def search(self, query_embedding: Any, top_k: int, max_distance: float) -> List[dict]: ...

    async def delete(self, id: str) -> None: ...

    async def clear(self) -> None: ...


class AbstractCache(abc.ABC):
    @abc.abstractmethod
    async def get(self, request: InferenceRequest) -> Optional[Tuple[InferenceResponse, CacheInfo]]:
        raise NotImplementedError

    @abc.abstractmethod
    async def set(self, request: InferenceRequest, response: InferenceResponse) -> None:
        raise NotImplementedError

    async def invalidate(self, pattern: Optional[str] = None) -> int:
        return 0

    def get_metrics(self) -> dict:
        return {}


