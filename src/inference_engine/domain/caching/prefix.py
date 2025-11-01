from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

import structlog

from ..models.cache import PrefixCacheEntry
from .base import AbstractCache


logger = structlog.get_logger()


class PrefixCache(AbstractCache):
    """Cache for common prompt prefixes to enable KV-cache reuse."""

    def __init__(self, max_entries: int = 1000) -> None:
        self.max_entries = max_entries
        self.prefix_cache: dict[str, PrefixCacheEntry] = {}
        self.hits = 0
        self.misses = 0

    async def get_prefix(self, text: str) -> Optional[PrefixCacheEntry]:
        for prefix_hash, entry in self.prefix_cache.items():
            if text.startswith(entry.prefix_text):
                object.__setattr__(entry, "last_used", datetime.utcnow())
                object.__setattr__(entry, "usage_count", entry.usage_count + 1)
                self.hits += 1
                logger.debug(
                    "prefix_cache_hit", prefix_hash=prefix_hash, prefix_length=entry.prefix_length, usage_count=entry.usage_count
                )
                return entry
        self.misses += 1
        return None

    async def set_prefix(self, prefix_text: str, kv_states: Optional[Any] = None) -> None:
        import hashlib

        prefix_hash = hashlib.sha256(prefix_text.encode()).hexdigest()[:16]
        entry = PrefixCacheEntry(
            prefix_hash=prefix_hash,
            prefix_text=prefix_text,
            prefix_length=len(prefix_text),
            kv_states=kv_states,
            tokens_saved_per_use=len(prefix_text) // 4,
        )
        self.prefix_cache[prefix_hash] = entry
        logger.debug("prefix_cached", prefix_hash=prefix_hash, prefix_length=entry.prefix_length)
        if len(self.prefix_cache) > self.max_entries:
            self._evict_lfu()

    def _evict_lfu(self) -> None:
        if not self.prefix_cache:
            return
        lfu_prefix_hash = min(self.prefix_cache.keys(), key=lambda k: self.prefix_cache[k].usage_count)
        del self.prefix_cache[lfu_prefix_hash]
        logger.debug("prefix_evicted", prefix_hash=lfu_prefix_hash)

    # AbstractCache interface (no-op implementations for compatibility)
    async def get(self, request):  # type: ignore[override]
        return None

    async def set(self, request, response):  # type: ignore[override]
        return None

    async def invalidate(self, pattern: Optional[str] = None) -> int:  # type: ignore[override]
        if pattern is None:
            count = len(self.prefix_cache)
            self.prefix_cache.clear()
            return count
        to_remove = [k for k, v in self.prefix_cache.items() if pattern in v.prefix_text]
        for k in to_remove:
            del self.prefix_cache[k]
        return len(to_remove)

    def get_metrics(self) -> dict:  # type: ignore[override]
        total_lookups = self.hits + self.misses
        hit_rate = self.hits / total_lookups if total_lookups > 0 else 0.0
        total_tokens_saved = sum(e.total_tokens_saved for e in self.prefix_cache.values())
        return {
            "cache_size": len(self.prefix_cache),
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate,
            "total_tokens_saved": total_tokens_saved,
        }


