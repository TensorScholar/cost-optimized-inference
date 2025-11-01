from __future__ import annotations

from typing import Optional, Tuple
from datetime import datetime
import structlog
import numpy as np

from ..models.cache import CacheEntry, CacheKey, CacheStrategy, SemanticCacheConfig
from ..models.request import InferenceRequest
from ..models.response import InferenceResponse, CacheInfo, UsageMetrics
from .base import AbstractCache, VectorStore


logger = structlog.get_logger()


class SemanticCache(AbstractCache):
    """Semantic similarity-based cache using vector embeddings."""

    def __init__(self, config: SemanticCacheConfig, embedding_function, vector_store: VectorStore):
        self.config = config
        self.embedding_function = embedding_function
        self.vector_store = vector_store
        self.cache_entries: dict[str, CacheEntry] = {}
        self.hits = 0
        self.misses = 0
        self.total_lookups = 0

    async def get(self, request: InferenceRequest) -> Optional[Tuple[InferenceResponse, CacheInfo]]:
        self.total_lookups += 1
        if not self.config.enabled:
            self.misses += 1
            return None
        text = request.prompt or str(request.messages)
        query_embedding = await self.embedding_function(text)
        similar_entries = await self.vector_store.search(
            query_embedding=query_embedding, top_k=5, max_distance=self.config.max_distance
        )
        if not similar_entries:
            self.misses += 1
            logger.debug("semantic_cache_miss", request_id=str(request.id))
            return None
        best_match = similar_entries[0]
        similarity_score = 1.0 - best_match["distance"]
        if similarity_score < self.config.similarity_threshold:
            self.misses += 1
            logger.debug(
                "semantic_cache_miss_threshold",
                request_id=str(request.id),
                best_similarity=similarity_score,
                threshold=self.config.similarity_threshold,
            )
            return None
        cache_entry_id = best_match["id"]
        cache_entry = self.cache_entries.get(cache_entry_id)
        if not cache_entry or cache_entry.is_expired:
            self.misses += 1
            return None
        cache_entry.touch()
        self.hits += 1
        response = InferenceResponse(
            request_id=request.id,
            text=cache_entry.response,
            model_used=cache_entry.model_used,
            usage=UsageMetrics(
                prompt_tokens=cache_entry.tokens_prompt,
                completion_tokens=cache_entry.tokens_completion,
                total_tokens=cache_entry.tokens_prompt + cache_entry.tokens_completion,
                cached_tokens=cache_entry.tokens_completion,
                cost_usd=0.0,
            ),
            cache_info=CacheInfo(
                hit=True,
                source="semantic",
                similarity_score=similarity_score,
                tokens_saved=cache_entry.tokens_completion,
                latency_saved_ms=500,
            ),
            latency_ms=5,
        )
        logger.info(
            "semantic_cache_hit",
            request_id=str(request.id),
            cache_entry_id=cache_entry_id,
            similarity_score=similarity_score,
            tokens_saved=cache_entry.tokens_completion,
        )
        return response, response.cache_info

    async def set(self, request: InferenceRequest, response: InferenceResponse) -> None:
        if not self.config.enabled:
            return
        text = request.prompt or str(request.messages)
        embedding = await self.embedding_function(text)
        cache_key = CacheKey.from_request(request)
        cache_entry = CacheEntry(
            key=cache_key,
            prompt=text,
            response=response.text,
            embedding=embedding,
            model_used=response.model_used,
            tokens_prompt=response.usage.prompt_tokens,
            tokens_completion=response.usage.completion_tokens,
            cost_usd=response.usage.cost_usd,
            strategy=CacheStrategy.SEMANTIC,
            ttl_seconds=request.cache_ttl_seconds,
        )
        self.cache_entries[str(cache_entry.id)] = cache_entry
        await self.vector_store.add(
            id=str(cache_entry.id),
            embedding=embedding,
            metadata={
                "prompt": text,
                "response": response.text,
                "model": response.model_used,
                "timestamp": cache_entry.created_at.isoformat(),
            },
        )
        logger.debug("semantic_cache_set", cache_entry_id=str(cache_entry.id), request_id=str(request.id))
        if len(self.cache_entries) > self.config.max_cache_size:
            await self._evict_lru()

    async def _evict_lru(self) -> None:
        if not self.cache_entries:
            return
        lru_entry = min(self.cache_entries.values(), key=lambda e: e.last_accessed)
        del self.cache_entries[str(lru_entry.id)]
        await self.vector_store.delete(str(lru_entry.id))
        logger.debug("cache_entry_evicted", entry_id=str(lru_entry.id), age_seconds=lru_entry.age_seconds)

    async def invalidate(self, pattern: Optional[str] = None) -> int:
        if pattern is None:
            count = len(self.cache_entries)
            self.cache_entries.clear()
            await self.vector_store.clear()
            return count
        to_remove = []
        for entry_id, entry in self.cache_entries.items():
            if pattern in entry.prompt or pattern in entry.response:
                to_remove.append(entry_id)
        for entry_id in to_remove:
            del self.cache_entries[entry_id]
            await self.vector_store.delete(entry_id)
        return len(to_remove)

    def get_metrics(self) -> dict:
        hit_rate = self.hits / self.total_lookups if self.total_lookups > 0 else 0.0
        return {
            "total_lookups": self.total_lookups,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate,
            "cache_size": len(self.cache_entries),
            "cache_memory_mb": self._estimate_memory_usage(),
        }

    def _estimate_memory_usage(self) -> float:
        if not self.cache_entries:
            return 0.0
        embedding_size_bytes = self.config.vector_dimension * 4
        avg_text_size = 1024
        total_bytes = len(self.cache_entries) * (avg_text_size + embedding_size_bytes)
        return total_bytes / (1024 * 1024)


