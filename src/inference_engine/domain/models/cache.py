from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Any
from uuid import UUID, uuid4
import numpy as np


class CacheStrategy(str, Enum):
    """Cache storage strategies"""

    EXACT = "exact"  # Exact match only
    SEMANTIC = "semantic"  # Semantic similarity matching
    PREFIX = "prefix"  # Common prefix matching
    HYBRID = "hybrid"  # Combination of strategies


class EvictionPolicy(str, Enum):
    """Cache eviction policies"""

    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    TTL = "ttl"  # Time To Live
    COST_AWARE = "cost_aware"  # Evict by cost/benefit ratio


@dataclass(frozen=True)
class CacheKey:
    """Composite cache key"""

    content_hash: str
    model: str
    temperature: float
    max_tokens: int

    def to_string(self) -> str:
        """Convert to string representation"""
        return f"{self.content_hash}:{self.model}:{self.temperature}:{self.max_tokens}"

    @classmethod
    def from_request(cls, request: "InferenceRequest") -> "CacheKey":
        """Create cache key from request"""
        import hashlib

        content = request.prompt or str(request.messages)
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

        return cls(
            content_hash=content_hash,
            model=request.preferred_model or "default",
            temperature=request.parameters.temperature,
            max_tokens=request.parameters.max_tokens,
        )


@dataclass
class CacheEntry:
    """Entry in the cache"""

    id: UUID = field(default_factory=uuid4)
    key: CacheKey

    # Content
    prompt: str
    response: str
    embedding: Optional[np.ndarray] = None

    # Metadata
    model_used: str = ""
    tokens_prompt: int = 0
    tokens_completion: int = 0
    cost_usd: float = 0.0

    # Cache management
    strategy: CacheStrategy = CacheStrategy.EXACT
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_accessed: datetime = field(default_factory=datetime.utcnow)
    access_count: int = 0
    ttl_seconds: Optional[int] = None

    # Quality metrics
    confidence_score: float = 1.0  # How confident we are in this cache

    @property
    def is_expired(self) -> bool:
        """Check if cache entry has expired"""
        if self.ttl_seconds is None:
            return False
        age = (datetime.utcnow() - self.created_at).total_seconds()
        return age > self.ttl_seconds

    @property
    def age_seconds(self) -> float:
        """Age of cache entry in seconds"""
        return (datetime.utcnow() - self.created_at).total_seconds()

    @property
    def time_since_access_seconds(self) -> float:
        """Time since last access in seconds"""
        return (datetime.utcnow() - self.last_accessed).total_seconds()

    @property
    def cost_savings(self) -> float:
        """Total cost saved by this cache entry"""
        return self.cost_usd * self.access_count

    def touch(self) -> None:
        """Update access timestamp and count (mutable operation)"""
        object.__setattr__(self, "last_accessed", datetime.utcnow())
        object.__setattr__(self, "access_count", self.access_count + 1)


@dataclass(frozen=True)
class CacheMetrics:
    """Cache performance metrics"""

    total_requests: int
    cache_hits: int
    cache_misses: int

    # By strategy
    exact_hits: int = 0
    semantic_hits: int = 0
    prefix_hits: int = 0

    # Performance
    avg_similarity_score: float = 0.0
    total_tokens_saved: int = 0
    total_cost_saved_usd: float = 0.0
    avg_latency_saved_ms: float = 0.0

    # Cache health
    cache_size: int = 0
    cache_memory_mb: float = 0.0
    evictions: int = 0

    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def hit_rate(self) -> float:
        """Overall cache hit rate"""
        if self.total_requests == 0:
            return 0.0
        return self.cache_hits / self.total_requests

    @property
    def miss_rate(self) -> float:
        """Cache miss rate"""
        return 1.0 - self.hit_rate


@dataclass(frozen=True)
class PrefixCacheEntry:
    """Specialized cache entry for common prefixes"""

    prefix_hash: str
    prefix_text: str
    prefix_length: int

    # KV cache state (if using vLLM/TGI)
    kv_states: Optional[Any] = None  # Actual tensor data

    # Usage tracking
    usage_count: int = 0
    last_used: datetime = field(default_factory=datetime.utcnow)

    # Cost savings
    tokens_saved_per_use: int = 0
    total_tokens_saved: int = 0


@dataclass
class SemanticCacheConfig:
    """Configuration for semantic caching"""

    enabled: bool = True
    similarity_threshold: float = 0.90
    max_distance: float = 0.15  # Cosine distance
    embedding_model: str = "all-MiniLM-L6-v2"
    vector_dimension: int = 384
    index_type: str = "faiss"  # or "qdrant", "milvus"
    max_cache_size: int = 10000


