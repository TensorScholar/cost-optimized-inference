from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from ...utils.time import utc_now


class ModelTier(StrEnum):
    ECONOMY = "economy"
    STANDARD = "standard"
    PREMIUM = "premium"

    @property
    def rank(self) -> int:
        return {
            ModelTier.ECONOMY: 1,
            ModelTier.STANDARD: 2,
            ModelTier.PREMIUM: 3,
        }[self]


class RoutingStrategy(StrEnum):
    COST_OPTIMAL = "cost_optimal"
    LATENCY_OPTIMAL = "latency_optimal"
    QUALITY_OPTIMAL = "quality_optimal"
    BALANCED = "balanced"
    ROUND_ROBIN = "round_robin"


@dataclass(frozen=True)
class ModelConfig:
    id: str
    name: str
    tier: ModelTier
    max_context_length: int
    supports_streaming: bool = True
    supports_batching: bool = True
    avg_latency_ms: int = 500
    max_throughput_rps: int = 100
    tokens_per_second: int = 50
    cost_per_1k_input_tokens: float = 0.001
    cost_per_1k_output_tokens: float = 0.002
    max_replicas: int = 3
    current_load: float = 0.0
    healthy: bool = True
    circuit_breaker_open: bool = False

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        input_cost = (input_tokens / 1000) * self.cost_per_1k_input_tokens
        output_cost = (output_tokens / 1000) * self.cost_per_1k_output_tokens
        return input_cost + output_cost

    @property
    def is_available(self) -> bool:
        return self.healthy and not self.circuit_breaker_open and self.current_load < 0.95


@dataclass(frozen=True)
class ComplexityEstimate:
    score: float
    factors: dict[str, float]
    input_length: int
    estimated_reasoning_steps: int
    requires_context: bool
    domain_specific: bool

    @property
    def recommended_tier(self) -> ModelTier:
        if self.score > 0.7:
            return ModelTier.PREMIUM
        if self.score > 0.3:
            return ModelTier.STANDARD
        return ModelTier.ECONOMY


@dataclass(frozen=True)
class RoutingDecision:
    request_id: UUID
    selected_model: ModelConfig
    strategy: RoutingStrategy
    complexity_estimate: ComplexityEstimate | None
    estimated_cost: float
    estimated_latency_ms: int
    estimated_quality_score: float
    decision_reason: str
    fallback_models: list[ModelConfig] = field(default_factory=list)
    considered_models: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=utc_now)
    id: UUID = field(default_factory=uuid4)
