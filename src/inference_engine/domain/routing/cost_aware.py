from typing import List
import structlog

from ..models.request import InferenceRequest
from ..models.routing import (
    ModelConfig,
    RoutingDecision,
    RoutingStrategy,
    ComplexityEstimate,
    ModelTier,
)
from .base import AbstractRouter
from .complexity import ComplexityEstimator


logger = structlog.get_logger()


class CostAwareRouter(AbstractRouter):
    """Routes requests to models based on cost optimization."""

    def __init__(self, models: List[ModelConfig], complexity_estimator: ComplexityEstimator, cost_weight: float = 0.7):
        self.models = {m.id: m for m in models}
        self.complexity_estimator = complexity_estimator
        self.cost_weight = cost_weight
        self.models_by_cost = sorted(models, key=lambda m: (m.cost_per_1k_input_tokens + m.cost_per_1k_output_tokens))

    async def route(self, request: InferenceRequest) -> RoutingDecision:
        complexity = await self.complexity_estimator.estimate(request)
        available_models = [
            m for m in self.models_by_cost if m.is_available and self._can_handle_request(m, request, complexity)
        ]
        if not available_models:
            available_models = [m for m in self.models.values() if m.healthy]
            if not available_models:
                raise RuntimeError("No healthy models available")
        selected = self._select_optimal_model(available_models, request, complexity)
        fallbacks = [m for m in available_models if m.id != selected.id][:3]
        estimated_cost = selected.calculate_cost(request.estimated_input_tokens, request.parameters.max_tokens)
        decision = RoutingDecision(
            request_id=request.id,
            selected_model=selected,
            fallback_models=fallbacks,
            strategy=RoutingStrategy.COST_OPTIMAL,
            complexity_estimate=complexity,
            estimated_cost=estimated_cost,
            estimated_latency_ms=selected.avg_latency_ms,
            estimated_quality_score=self._estimate_quality(selected, complexity),
            decision_reason=self._generate_reason(selected, complexity),
            considered_models=[m.id for m in available_models],
        )
        logger.info(
            "routing_decision",
            request_id=str(request.id),
            selected_model=selected.id,
            complexity_score=complexity.score,
            estimated_cost=estimated_cost,
            fallback_count=len(fallbacks),
        )
        return decision

    def _can_handle_request(self, model: ModelConfig, request: InferenceRequest, complexity: ComplexityEstimate) -> bool:
        total_tokens = request.estimated_input_tokens + request.parameters.max_tokens
        if total_tokens > model.max_context_length:
            return False
        required_tier = complexity.recommended_tier
        if required_tier == ModelTier.PREMIUM and model.tier == ModelTier.ECONOMY:
            return False
        return True

    def _select_optimal_model(
        self, models: List[ModelConfig], request: InferenceRequest, complexity: ComplexityEstimate
    ) -> ModelConfig:
        scores = []
        min_cost = min(m.cost_per_1k_input_tokens for m in models)
        max_cost = max(m.cost_per_1k_input_tokens for m in models)
        for model in models:
            normalized_cost = (model.cost_per_1k_input_tokens - min_cost) / (max_cost - min_cost + 1e-6)
            quality_score = self._estimate_quality(model, complexity)
            score = self.cost_weight * normalized_cost + (1 - self.cost_weight) * (1 - quality_score)
            load_penalty = model.current_load * 0.2
            score += load_penalty
            scores.append((score, model))
        return min(scores, key=lambda x: x[0])[1]

    def _estimate_quality(self, model: ModelConfig, complexity: ComplexityEstimate) -> float:
        tier_scores = {ModelTier.PREMIUM: 1.0, ModelTier.STANDARD: 0.7, ModelTier.ECONOMY: 0.4}
        base_score = tier_scores.get(model.tier, 0.5)
        recommended_tier = complexity.recommended_tier
        if model.tier == recommended_tier:
            return base_score
        elif model.tier.value > recommended_tier.value:
            return min(1.0, base_score + 0.1)
        else:
            return max(0.0, base_score - 0.2)

    def _generate_reason(self, model: ModelConfig, complexity: ComplexityEstimate) -> str:
        reasons = []
        reasons.append(f"Selected {model.name} ({model.tier.value} tier)")
        reasons.append(f"Complexity score: {complexity.score:.2f}")
        reasons.append(f"Estimated cost: ${model.cost_per_1k_input_tokens:.4f}/1K tokens")
        if complexity.score < 0.3:
            reasons.append("Simple query - economy model sufficient")
        elif complexity.score < 0.7:
            reasons.append("Moderate complexity - standard model appropriate")
        else:
            reasons.append("High complexity - premium model required")
        if model.current_load > 0.7:
            reasons.append(f"High load ({model.current_load:.0%}) - may have queuing")
        return "; ".join(reasons)

    async def update_model_health(self, model_id: str, healthy: bool, circuit_breaker_open: bool = False) -> None:
        if model_id in self.models:
            model = self.models[model_id]
            object.__setattr__(model, "healthy", healthy)
            object.__setattr__(model, "circuit_breaker_open", circuit_breaker_open)
            logger.info("model_health_updated", model_id=model_id, healthy=healthy, circuit_breaker_open=circuit_breaker_open)

    async def update_model_load(self, model_id: str, load: float) -> None:
        if model_id in self.models:
            model = self.models[model_id]
            object.__setattr__(model, "current_load", load)
            logger.debug("model_load_updated", model_id=model_id, load=load)
