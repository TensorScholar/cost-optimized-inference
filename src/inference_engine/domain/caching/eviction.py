from abc import ABC, abstractmethod
from typing import List, Dict, Any
from datetime import datetime
import structlog

from ..models.cache import CacheEntry

logger = structlog.get_logger()


class EvictionPolicy(ABC):
    """Abstract base class for cache eviction policies."""

    @abstractmethod
    def should_evict(self, entry: CacheEntry) -> bool:
        """Check if entry should be evicted."""
        raise NotImplementedError

    @abstractmethod
    def select_to_evict(self, entries: List[CacheEntry]) -> CacheEntry:
        """Select entry to evict from candidates."""
        raise NotImplementedError


class LRUEvictionPolicy(EvictionPolicy):
    """Least Recently Used eviction policy."""

    def should_evict(self, entry: CacheEntry) -> bool:
        return False  # LRU evicts on-demand, not by checking individual entries

    def select_to_evict(self, entries: List[CacheEntry]) -> CacheEntry:
        if not entries:
            raise ValueError("Cannot evict from empty list")

        lru = min(entries, key=lambda e: e.last_accessed)
        logger.debug("lru_eviction", entry_id=str(lru.id), last_accessed=lru.last_accessed)
        return lru


class LFUEvictionPolicy(EvictionPolicy):
    """Least Frequently Used eviction policy."""

    def should_evict(self, entry: CacheEntry) -> bool:
        return False

    def select_to_evict(self, entries: List[CacheEntry]) -> CacheEntry:
        if not entries:
            raise ValueError("Cannot evict from empty list")

        lfu = min(entries, key=lambda e: e.access_count)
        logger.debug("lfu_eviction", entry_id=str(lfu.id), access_count=lfu.access_count)
        return lfu


class TTL_EvictionPolicy(EvictionPolicy):
    """Time To Live eviction policy."""

    def should_evict(self, entry: CacheEntry) -> bool:
        if entry.ttl_seconds is None:
            return False

        age = (datetime.utcnow() - entry.created_at).total_seconds()
        return age > entry.ttl_seconds

    def select_to_evict(self, entries: List[CacheEntry]) -> CacheEntry:
        if not entries:
            raise ValueError("Cannot evict from empty list")

        # Select expired entry if any, otherwise oldest
        expired = [e for e in entries if self.should_evict(e)]
        if expired:
            oldest_expired = max(expired, key=lambda e: e.created_at)
            logger.debug("ttl_eviction", entry_id=str(oldest_expired.id), age=oldest_expired.age_seconds)
            return oldest_expired

        oldest = max(entries, key=lambda e: e.created_at)
        logger.debug("ttl_eviction_oldest", entry_id=str(oldest.id))
        return oldest


class CostAwareEvictionPolicy(EvictionPolicy):
    """Evict based on cost-benefit ratio."""

    def should_evict(self, entry: CacheEntry) -> bool:
        return False

    def select_to_evict(self, entries: List[CacheEntry]) -> CacheEntry:
        if not entries:
            raise ValueError("Cannot evict from empty list")

        # Calculate cost-benefit score (lower is worse, evict first)
        # Benefit = cost_saved * access_count
        # Score = benefit / age_seconds (benefit per second)
        def score(e: CacheEntry) -> float:
            if e.age_seconds == 0:
                return float("inf")
            benefit = e.cost_savings
            return benefit / e.age_seconds

        worst = min(entries, key=score)
        logger.debug("cost_aware_eviction", entry_id=str(worst.id), score=score(worst))
        return worst

