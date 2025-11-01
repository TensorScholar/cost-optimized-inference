from __future__ import annotations

from typing import Optional, Tuple

import structlog

from ..models.cache import CacheEntry, CacheKey, CacheStrategy
from ..models.request import InferenceRequest
from ..models.response import InferenceResponse, CacheInfo, UsageMetrics
from .base import AbstractCache


logger = structlog.get_logger()


class ExactCache(AbstractCache):
    """Exact match cache for duplicate requests."""

    def __init__(self, max_entries: int = 10000):
        self.max_entries = max_entries
        self.cache: dict[str, CacheEntry] = {}
        self.hits = 0
        self.misses = 0

    async def get(self, request: InferenceRequest) -> Optional[Tuple[InferenceResponse, CacheInfo]]:
        cache_key_str = request.cache_key
        entry = self.cache.get(cache_key_str)
        if entry is None or entry.is_expired:
            self.misses += 1
            return None
        entry.touch()
        self.hits += 1
        response = InferenceResponse(
            request_id=request.id,
            text=entry.response,
            model_used=entry.model_used,
            usage=UsageMetrics(
                prompt_tokens=entry.tokens_prompt,
                completion_tokens=entry.tokens_completion,
                total_tokens=entry.tokens_prompt + entry.tokens_completion,
                cached_tokens=entry.tokens_completion,
                cost_usd=0.0,
            ),
            cache_info=CacheInfo(
                hit=True,
                source="exact",
                similarity_score=1.0,
                tokens_saved=entry.tokens_completion,
                latency_saved_ms=500,
            ),
            latency_ms=1,
        )
        logger.info(
            "exact_cache_hit", request_id=str(request.id), cache_key=cache_key_str[:16], tokens_saved=entry.tokens_completion
        )
        return response, response.cache_info

    async def set(self, request: InferenceRequest, response: InferenceResponse) -> None:
        cache_key_str = request.cache_key
        cache_key = CacheKey.from_request(request)
        text = request.prompt or str(request.messages)
        entry = CacheEntry(
            key=cache_key,
            prompt=text,
            response=response.text,
            model_used=response.model_used,
            tokens_prompt=response.usage.prompt_tokens,
            tokens_completion=response.usage.completion_tokens,
            cost_usd=response.usage.cost_usd,
            strategy=CacheStrategy.EXACT,
            ttl_seconds=request.cache_ttl_seconds,
        )
        self.cache[cache_key_str] = entry
        logger.debug("exact_cache_set", cache_key=cache_key_str[:16], request_id=str(request.id))
        if len(self.cache) > self.max_entries:
            self._evict_lru()

    def _evict_lru(self) -> None:
        if not self.cache:
            return
        lru_key = min(self.cache.keys(), key=lambda k: self.cache[k].last_accessed)
        del self.cache[lru_key]
        logger.debug("exact_cache_evicted", cache_key=lru_key[:16])

    async def invalidate(self, pattern: Optional[str] = None) -> int:
        if pattern is None:
            count = len(self.cache)
            self.cache.clear()
            return count
        to_remove = [k for k, v in self.cache.items() if pattern in v.prompt or pattern in v.response]
        for key in to_remove:
            del self.cache[key]
        return len(to_remove)

    def get_metrics(self) -> dict:
        total_lookups = self.hits + self.misses
        hit_rate = self.hits / total_lookups if total_lookups > 0 else 0.0
        return {"cache_size": len(self.cache), "hits": self.hits, "misses": self.misses, "hit_rate": hit_rate}


