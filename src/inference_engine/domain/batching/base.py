from __future__ import annotations

import abc
from typing import Optional

from ..models.request import InferenceRequest
from ..models.batch import BatchRequest, BatchMetrics


class AbstractBatcher(abc.ABC):
    @abc.abstractmethod
    async def add_request(self, request: InferenceRequest) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    async def collect_batch(self) -> Optional[BatchRequest]:
        raise NotImplementedError

    async def record_batch_metrics(self, metrics: BatchMetrics) -> None:
        # Optional: batchers may adjust internal state based on metrics
        return None

    def get_queue_stats(self) -> dict:
        return {}


