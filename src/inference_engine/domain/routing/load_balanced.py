from typing import List
import structlog

from ..models.request import InferenceRequest
from ..models.routing import ModelConfig, RoutingDecision, RoutingStrategy, ModelTier
from .base import AbstractRouter


logger = structlog.get_logger()


class LoadBalancedRouter(AbstractRouter):
    """
    Round-robin load balancing across available models.

    Distributes requests evenly to prevent overloading any single instance.
    """

    def __init__(self, models: List[ModelConfig]) -> None:
        self.models = models
        self.current_index = 0

    async def route(self, request: InferenceRequest) -> RoutingDecision:
        available = [m for m in self.models if m.is_available]

        if not available:
            raise RuntimeError("No available models for routing")

        # Round-robin selection
        selected = available[self.current_index % len(available)]
        self.current_index += 1

        logger.info(
            "load_balanced_routing",
            request_id=str(request.id),
            model=selected.id,
            index=self.current_index,
        )

        return RoutingDecision(
            request_id=request.id,
            selected_model=selected,
            fallback_models=[],
            strategy=RoutingStrategy.ROUND_ROBIN,
            complexity_estimate=None,
            estimated_cost=selected.calculate_cost(
                request.estimated_input_tokens, request.parameters.max_tokens
            ),
            estimated_latency_ms=selected.avg_latency_ms,
            estimated_quality_score=0.7,
            decision_reason=f"Round-robin selection: {selected.id}",
            considered_models=[m.id for m in available],
        )

