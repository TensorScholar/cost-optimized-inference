from __future__ import annotations

import structlog

from ..models.request import InferenceRequest
from ..models.routing import (
    ComplexityEstimate,
    ModelConfig,
    ModelTier,
    RoutingDecision,
    RoutingStrategy,
)
from .base import AbstractRouter
from .complexity import ComplexityEstimator

logger = structlog.get_logger()


class CostAwareRouter(AbstractRouter):
    """Route to the cheapest available model that can plausibly satisfy the request."""

    def __init__(
        self,
        models: list[ModelConfig],
        complexity_estimator: ComplexityEstimator,
        cost_weight: float = 0.7,
    ) -> None:
        self.models = {model.id: model for model in models}
        self.complexity_estimator = complexity_estimator
        self.cost_weight = cost_weight
        self.models_by_cost = sorted(
            models,
            key=lambda model: model.cost_per_1k_input_tokens + model.cost_per_1k_output_tokens,
        )

    async def route(self, request: InferenceRequest) -> RoutingDecision:
        complexity = await self.complexity_estimator.estimate(request)
        available = [
            model
            for model in self.models_by_cost
            if model.is_available and self._can_handle_request(model, request, complexity)
        ]
        if not available:
            available = [model for model in self.models_by_cost if model.healthy]
        if not available:
            raise RuntimeError("No healthy models available")

        selected = self._select_optimal_model(available, request, complexity)
        estimated_cost = selected.calculate_cost(
            request.estimated_input_tokens, request.parameters.max_tokens
        )
        decision = RoutingDecision(
            request_id=request.id,
            selected_model=selected,
            fallback_models=[model for model in available if model.id != selected.id][:3],
            strategy=RoutingStrategy.COST_OPTIMAL,
            complexity_estimate=complexity,
            estimated_cost=estimated_cost,
            estimated_latency_ms=selected.avg_latency_ms,
            estimated_quality_score=self._estimate_quality(selected, complexity),
            decision_reason=self._generate_reason(selected, complexity),
            considered_models=[model.id for model in available],
        )
        logger.debug("routing_decision", selected_model=selected.id, cost=estimated_cost)
        return decision

    def _can_handle_request(
        self, model: ModelConfig, request: InferenceRequest, complexity: ComplexityEstimate
    ) -> bool:
        total_tokens = request.estimated_input_tokens + request.parameters.max_tokens
        if total_tokens > model.max_context_length:
            return False
        return not (
            complexity.recommended_tier == ModelTier.PREMIUM and model.tier == ModelTier.ECONOMY
        )

    def _select_optimal_model(
        self, models: list[ModelConfig], _request: InferenceRequest, complexity: ComplexityEstimate
    ) -> ModelConfig:
        min_cost = min(model.cost_per_1k_input_tokens for model in models)
        max_cost = max(model.cost_per_1k_input_tokens for model in models)
        scored: list[tuple[float, ModelConfig]] = []
        for model in models:
            normalized_cost = (model.cost_per_1k_input_tokens - min_cost) / (
                max_cost - min_cost + 1e-9
            )
            quality_score = self._estimate_quality(model, complexity)
            score = self.cost_weight * normalized_cost + (1 - self.cost_weight) * (
                1 - quality_score
            )
            score += model.current_load * 0.2
            scored.append((score, model))
        return min(scored, key=lambda item: item[0])[1]

    def _estimate_quality(self, model: ModelConfig, complexity: ComplexityEstimate) -> float:
        tier_scores = {
            ModelTier.ECONOMY: 0.4,
            ModelTier.STANDARD: 0.7,
            ModelTier.PREMIUM: 1.0,
        }
        base_score = tier_scores[model.tier]
        recommended = complexity.recommended_tier
        if model.tier == recommended:
            return base_score
        if model.tier.rank > recommended.rank:
            return min(1.0, base_score + 0.1)
        return max(0.0, base_score - 0.2)

    def _generate_reason(self, model: ModelConfig, complexity: ComplexityEstimate) -> str:
        return (
            f"Selected {model.name} ({model.tier.value}) with complexity "
            f"{complexity.score:.2f}"
        )
