from __future__ import annotations

import asyncio
from typing import List, Optional, Dict, Callable, Awaitable
import numpy as np
from sklearn.cluster import DBSCAN
import structlog

from ..models.request import InferenceRequest
from ..models.batch import BatchRequest, BatchStrategy
from .base import AbstractBatcher


logger = structlog.get_logger()


class SemanticBatcher(AbstractBatcher):
    """
    Groups requests by semantic similarity to maximize KV-cache reuse.
    """

    def __init__(self, strategy: BatchStrategy, embedding_function: Callable[[str], Awaitable[np.ndarray]]):
        self.strategy = strategy
        self.embedding_function = embedding_function
        self.pending_requests: List[InferenceRequest] = []
        self.request_embeddings: Dict[str, np.ndarray] = {}
        self.eps = 1.0 - strategy.similarity_threshold
        self.min_samples = strategy.min_batch_size

    async def add_request(self, request: InferenceRequest) -> None:
        self.pending_requests.append(request)
        text = request.prompt or str(request.messages)
        embedding = await self.embedding_function(text)
        self.request_embeddings[str(request.id)] = embedding
        logger.debug(
            "request_added_for_clustering",
            request_id=str(request.id),
            pending_count=len(self.pending_requests),
        )

    async def collect_batch(self) -> Optional[BatchRequest]:
        if len(self.pending_requests) < self.strategy.min_batch_size:
            return None
        request_ids = [str(r.id) for r in self.pending_requests]
        embeddings = np.array([self.request_embeddings[rid] for rid in request_ids])
        clustering = DBSCAN(eps=self.eps, min_samples=self.min_samples, metric="cosine").fit(embeddings)
        labels = clustering.labels_
        positive = labels[labels >= 0]
        if positive.size == 0:
            return await self._collect_simple_batch()
        unique_labels, counts = np.unique(positive, return_counts=True)
        largest_cluster_label = unique_labels[np.argmax(counts)]
        cluster_indices = np.where(labels == largest_cluster_label)[0]
        batch_requests = [self.pending_requests[i] for i in cluster_indices]
        for i in sorted(cluster_indices, reverse=True):
            request = self.pending_requests.pop(i)
            self.request_embeddings.pop(str(request.id), None)
        centroid = np.mean([embeddings[i] for i in cluster_indices], axis=0)
        common_prefix = self._find_common_prefix([r.prompt for r in batch_requests if r.prompt])
        batch = BatchRequest(
            requests=batch_requests,
            strategy=self.strategy,
            centroid_embedding=centroid,
            common_prefix=common_prefix,
        )
        logger.info(
            "semantic_batch_collected",
            batch_id=str(batch.id),
            size=batch.size,
            cluster_label=int(largest_cluster_label),
            common_prefix_length=len(common_prefix) if common_prefix else 0,
        )
        return batch

    async def _collect_simple_batch(self) -> BatchRequest:
        size = min(self.strategy.max_batch_size, len(self.pending_requests))
        batch_requests = self.pending_requests[:size]
        self.pending_requests = self.pending_requests[size:]
        for request in batch_requests:
            self.request_embeddings.pop(str(request.id), None)
        return BatchRequest(requests=batch_requests, strategy=self.strategy)

    def _find_common_prefix(self, texts: List[str]) -> Optional[str]:
        if not texts:
            return None
        min_length = min(len(t) for t in texts)
        prefix_length = 0
        for i in range(min_length):
            if all(t[i] == texts[0][i] for t in texts):
                prefix_length = i + 1
            else:
                break
        if prefix_length > 10:
            return texts[0][:prefix_length]
        return None


