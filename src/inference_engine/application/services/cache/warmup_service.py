from typing import List
import structlog

from ....domain.caching.semantic import SemanticCache
from ....domain.caching.prefix import PrefixCache

logger = structlog.get_logger()


class CacheWarmupService:
    """Service for pre-warming caches with common queries."""

    def __init__(
        self,
        semantic_cache: SemanticCache,
        prefix_cache: PrefixCache,
    ):
        self.semantic_cache = semantic_cache
        self.prefix_cache = prefix_cache

    async def warmup_common_queries(self, queries: List[str]) -> None:
        """Warm up cache with common queries."""
        logger.info("cache_warmup_started", query_count=len(queries))

        for query in queries:
            # Store in semantic cache
            # Implementation would compute embeddings and store
            pass

        logger.info("cache_warmup_completed")

    async def warmup_prefixes(self, prefixes: List[str]) -> None:
        """Warm up prefix cache with common system prompts."""
        logger.info("prefix_warmup_started", prefix_count=len(prefixes))

        for prefix in prefixes:
            await self.prefix_cache.set_prefix(prefix)

        logger.info("prefix_warmup_completed")

