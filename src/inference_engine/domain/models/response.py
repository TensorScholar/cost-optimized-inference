from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4


@dataclass(frozen=True)
class CacheInfo:
    """Information about cache usage"""

    hit: bool
    source: Optional[str] = None  # "exact", "semantic", "prefix"
    similarity_score: Optional[float] = None
    tokens_saved: int = 0
    latency_saved_ms: int = 0


@dataclass(frozen=True)
class UsageMetrics:
    """Token usage and cost metrics"""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cached_tokens: int = 0
    cost_usd: float = 0.0

    @property
    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        if self.total_tokens == 0:
            return 0.0
        return self.cached_tokens / self.total_tokens


@dataclass(frozen=True)
class InferenceResponse:
    """Complete inference response"""

    id: UUID = field(default_factory=uuid4)
    request_id: UUID
    text: str
    finish_reason: str = "stop"
    model_used: str = ""

    # Metrics
    usage: UsageMetrics
    cache_info: CacheInfo
    latency_ms: int

    # Timing breakdown
    queue_time_ms: int = 0
    inference_time_ms: int = 0
    postprocess_time_ms: int = 0

    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def total_cost_usd(self) -> float:
        """Total cost for this request"""
        return self.usage.cost_usd

    @property
    def cost_saved_usd(self) -> float:
        """Cost saved due to caching"""
        if not self.cache_info.hit:
            return 0.0
        token_price = 0.002 / 1000  # Example: $0.002 per 1K tokens
        return self.cache_info.tokens_saved * token_price


