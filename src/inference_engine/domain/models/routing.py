from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID, uuid4


class ModelTier(str, Enum):
    """Model tiers by capability and cost"""

    PREMIUM = "premium"  # GPT-4, Claude 3 Opus
    STANDARD = "standard"  # GPT-3.5, Claude 3 Sonnet
    ECONOMY = "economy"  # Smaller models


class RoutingStrategy(str, Enum):
    """Strategies for model selection"""

    COST_OPTIMAL = "cost_optimal"
    LATENCY_OPTIMAL = "latency_optimal"
    QUALITY_OPTIMAL = "quality_optimal"
    BALANCED = "balanced"
    ROUND_ROBIN = "round_robin"


@dataclass(frozen=True)
class ModelConfig:
    """Configuration for a model backend"""

    id: str
    name: str
    tier: ModelTier

    # Capabilities
    max_context_length: int
    supports_streaming: bool = True
    supports_batching: bool = True

    # Performance characteristics
    avg_latency_ms: int = 500
    max_throughput_rps: int = 100
    tokens_per_second: int = 50

    # Cost (per 1K tokens)
    cost_per_1k_input_tokens: float = 0.001
    cost_per_1k_output_tokens: float = 0.002

    # Availability
    max_replicas: int = 3
    current_load: float = 0.0  # 0.0 to 1.0

    # Health
    healthy: bool = True
    circuit_breaker_open: bool = False

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost for given token counts"""
        input_cost = (input_tokens / 1000) * self.cost_per_1k_input_tokens
        output_cost = (output_tokens / 1000) * self.cost_per_1k_output_tokens
        return input_cost + output_cost

    @property
    def is_available(self) -> bool:
        """Check if model is available for routing"""
        return self.healthy and not self.circuit_breaker_open and self.current_load < 0.95


@dataclass(frozen=True)
class ComplexityEstimate:
    """Estimated complexity of a request"""

    score: float  # 0.0 to 1.0, higher = more complex
    factors: Dict[str, float]

    # Specific complexity indicators
    input_length: int
    estimated_reasoning_steps: int
    requires_context: bool
    domain_specific: bool

    @property
    def recommended_tier(self) -> ModelTier:
        """Recommend model tier based on complexity"""
        if self.score > 0.7:
            return ModelTier.PREMIUM
        elif self.score > 0.3:
            return ModelTier.STANDARD
        else:
            return ModelTier.ECONOMY


@dataclass(frozen=True)
class RoutingDecision:
    """Decision about which model to use"""

    id: UUID = field(default_factory=uuid4)
    request_id: UUID

    # Selected model
    selected_model: ModelConfig
    fallback_models: List[ModelConfig] = field(default_factory=list)

    # Decision factors
    strategy: RoutingStrategy
    complexity_estimate: ComplexityEstimate

    # Cost-benefit analysis
    estimated_cost: float
    estimated_latency_ms: int
    estimated_quality_score: float

    # Reasoning
    decision_reason: str
    considered_models: List[str] = field(default_factory=list)

    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class LoadBalancerState:
    """State of load balancer for a model"""

    model_id: str

    # Current state
    active_requests: int = 0
    total_capacity: int = 100
    current_load: float = 0.0

    # Health tracking
    consecutive_failures: int = 0
    last_health_check: datetime = field(default_factory=datetime.utcnow)

    # Circuit breaker
    circuit_breaker_open: bool = False
    circuit_breaker_until: Optional[datetime] = None

    @property
    def is_healthy(self) -> bool:
        """Check if model is healthy"""
        return not self.circuit_breaker_open and self.consecutive_failures < 5

    @property
    def available_capacity(self) -> int:
        """Available request capacity"""
        return max(0, self.total_capacity - self.active_requests)

    def update_load(self) -> None:
        """Update current load percentage"""
        if self.total_capacity > 0:
            object.__setattr__(self, "current_load", self.active_requests / self.total_capacity)


