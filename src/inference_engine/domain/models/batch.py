from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

import numpy as np

from .request import InferenceRequest, RequestPriority


@dataclass(frozen=True)
class BatchStrategy:
    """Configuration for batching behavior"""

    min_batch_size: int = 4
    max_batch_size: int = 64
    max_wait_ms: int = 50

    # Adaptive parameters
    target_latency_p95_ms: int = 100
    enable_semantic_grouping: bool = True
    similarity_threshold: float = 0.85

    # Priority handling
    priority_lanes: bool = True
    express_max_wait_ms: int = 10

    def __post_init__(self) -> None:
        if self.min_batch_size > self.max_batch_size:
            raise ValueError("min_batch_size cannot exceed max_batch_size")


@dataclass
class BatchRequest:
    """A batch of requests to process together"""

    id: UUID = field(default_factory=uuid4)
    requests: List[InferenceRequest] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    strategy: BatchStrategy = field(default_factory=BatchStrategy)

    # Semantic grouping metadata
    centroid_embedding: Optional[np.ndarray] = None
    common_prefix: Optional[str] = None

    @property
    def size(self) -> int:
        """Number of requests in batch"""
        return len(self.requests)

    @property
    def priority(self) -> RequestPriority:
        """Highest priority in batch"""
        if not self.requests:
            return RequestPriority.STANDARD
        priorities = [r.priority for r in self.requests]
        if RequestPriority.EXPRESS in priorities:
            return RequestPriority.EXPRESS
        elif RequestPriority.STANDARD in priorities:
            return RequestPriority.STANDARD
        return RequestPriority.BATCH

    @property
    def estimated_tokens(self) -> int:
        """Total estimated tokens for batch"""
        return sum(r.estimated_input_tokens for r in self.requests)

    @property
    def age_ms(self) -> int:
        """Age of oldest request in batch"""
        now = datetime.utcnow()
        return int((now - self.created_at).total_seconds() * 1000)

    def can_add(self, request: InferenceRequest) -> bool:
        """Check if request can be added to this batch"""
        if self.size >= self.strategy.max_batch_size:
            return False
        if self.priority == RequestPriority.EXPRESS and request.priority != RequestPriority.EXPRESS:
            return False
        return True


@dataclass
class BatchMetrics:
    """Metrics for batch processing"""

    batch_id: UUID
    size: int
    total_tokens: int
    processing_time_ms: int
    wait_time_ms: int
    throughput_tokens_per_sec: float
    efficiency_score: float  # How well-utilized was the batch

    timestamp: datetime = field(default_factory=datetime.utcnow)


