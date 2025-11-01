import asyncio
from collections import deque
from datetime import datetime
import structlog
from typing import Optional

from ..models.request import InferenceRequest, RequestPriority
from ..models.batch import BatchRequest, BatchStrategy, BatchMetrics
from .base import AbstractBatcher


logger = structlog.get_logger()


class AdaptiveBatcher(AbstractBatcher):
    """
    Adaptive batching that dynamically adjusts batch size based on:
    1. Current queue depth
    2. Recent latency measurements
    3. System load
    4. Request priority
    """

    def __init__(self, strategy: BatchStrategy):
        self.strategy = strategy
        self.express_queue: deque[InferenceRequest] = deque()
        self.standard_queue: deque[InferenceRequest] = deque()
        self.batch_queue: deque[InferenceRequest] = deque()
        self.current_batch_size = strategy.min_batch_size
        self.recent_latencies: deque[int] = deque(maxlen=100)
        self.total_batches = 0
        self.total_requests = 0
        self._running = False

    async def add_request(self, request: InferenceRequest) -> None:
        if request.priority == RequestPriority.EXPRESS:
            self.express_queue.append(request)
        elif request.priority == RequestPriority.STANDARD:
            self.standard_queue.append(request)
        else:
            self.batch_queue.append(request)
        logger.debug(
            "request_queued",
            request_id=str(request.id),
            priority=request.priority.value,
            queue_sizes={
                "express": len(self.express_queue),
                "standard": len(self.standard_queue),
                "batch": len(self.batch_queue),
            },
        )

    async def collect_batch(self) -> Optional[BatchRequest]:
        if len(self.express_queue) >= 1:
            return await self._collect_express_batch()
        if len(self.standard_queue) >= self.current_batch_size:
            return await self._collect_standard_batch()
        if len(self.batch_queue) >= self.strategy.max_batch_size:
            return await self._collect_batch_batch()
        return await self._collect_mixed_batch()

    async def _collect_express_batch(self) -> BatchRequest:
        requests = []
        max_size = min(4, len(self.express_queue))
        for _ in range(max_size):
            if self.express_queue:
                requests.append(self.express_queue.popleft())
        batch = BatchRequest(
            requests=requests,
            strategy=BatchStrategy(
                min_batch_size=1, max_batch_size=4, max_wait_ms=self.strategy.express_max_wait_ms
            ),
        )
        logger.info("express_batch_collected", batch_id=str(batch.id), size=batch.size)
        return batch

    async def _collect_standard_batch(self) -> BatchRequest:
        requests = []
        target_size = self._calculate_optimal_batch_size()
        for _ in range(min(target_size, len(self.standard_queue))):
            requests.append(self.standard_queue.popleft())
        batch = BatchRequest(requests=requests, strategy=self.strategy)
        logger.info(
            "standard_batch_collected",
            batch_id=str(batch.id),
            size=batch.size,
            target_size=target_size,
        )
        return batch

    async def _collect_batch_batch(self) -> BatchRequest:
        requests = []
        max_size = min(self.strategy.max_batch_size, len(self.batch_queue))
        for _ in range(max_size):
            requests.append(self.batch_queue.popleft())
        batch = BatchRequest(requests=requests, strategy=self.strategy)
        logger.info("batch_batch_collected", batch_id=str(batch.id), size=batch.size)
        return batch

    async def _collect_mixed_batch(self) -> Optional[BatchRequest]:
        requests = []
        oldest_age_ms = self._get_oldest_request_age_ms()
        if oldest_age_ms < self.strategy.max_wait_ms:
            return None
        target_size = self._calculate_optimal_batch_size()
        while len(requests) < target_size and self.standard_queue:
            requests.append(self.standard_queue.popleft())
        while len(requests) < target_size and self.batch_queue:
            requests.append(self.batch_queue.popleft())
        if not requests:
            return None
        batch = BatchRequest(requests=requests, strategy=self.strategy)
        logger.info(
            "mixed_batch_collected",
            batch_id=str(batch.id),
            size=batch.size,
            oldest_age_ms=oldest_age_ms,
        )
        return batch

    def _calculate_optimal_batch_size(self) -> int:
        if not self.recent_latencies:
            return self.strategy.min_batch_size
        sorted_latencies = sorted(self.recent_latencies)
        p95_index = int(len(sorted_latencies) * 0.95)
        p95_index = min(max(p95_index, 0), len(sorted_latencies) - 1)
        p95_latency = sorted_latencies[p95_index]
        target = self.strategy.target_latency_p95_ms
        if p95_latency < target * 0.8:
            self.current_batch_size = min(self.strategy.max_batch_size, int(self.current_batch_size * 1.2))
        elif p95_latency > target:
            self.current_batch_size = max(self.strategy.min_batch_size, int(self.current_batch_size * 0.8))
        logger.debug(
            "batch_size_adjusted",
            current_size=self.current_batch_size,
            p95_latency=p95_latency,
            target_latency=target,
        )
        return self.current_batch_size

    def _get_oldest_request_age_ms(self) -> int:
        oldest = None
        for queue in [self.express_queue, self.standard_queue, self.batch_queue]:
            if queue:
                request = queue[0]
                if oldest is None or request.timestamp < oldest.timestamp:
                    oldest = request
        if oldest is None:
            return 0
        age = (datetime.utcnow() - oldest.timestamp).total_seconds() * 1000
        return int(age)

    async def record_batch_metrics(self, metrics: BatchMetrics) -> None:
        self.recent_latencies.append(metrics.processing_time_ms)
        self.total_batches += 1
        self.total_requests += metrics.size
        logger.info(
            "batch_metrics_recorded",
            batch_id=str(metrics.batch_id),
            size=metrics.size,
            processing_time_ms=metrics.processing_time_ms,
            throughput=metrics.throughput_tokens_per_sec,
        )

    def get_queue_stats(self) -> dict:
        return {
            "express": len(self.express_queue),
            "standard": len(self.standard_queue),
            "batch": len(self.batch_queue),
            "total": len(self.express_queue) + len(self.standard_queue) + len(self.batch_queue),
            "current_batch_size": self.current_batch_size,
            "total_batches": self.total_batches,
            "total_requests": self.total_requests,
        }


