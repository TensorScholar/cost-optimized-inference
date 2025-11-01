from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID, uuid4


@dataclass(frozen=True)
class CostBreakdown:
    """Detailed cost breakdown"""

    inference_cost: float  # Actual LLM API cost
    compute_cost: float  # Our infrastructure cost
    cache_savings: float  # Cost saved via caching
    optimization_savings: float  # Cost saved via batching/routing

    @property
    def total_cost(self) -> float:
        """Total cost before savings"""
        return self.inference_cost + self.compute_cost

    @property
    def net_cost(self) -> float:
        """Net cost after savings"""
        return self.total_cost - self.cache_savings - self.optimization_savings

    @property
    def savings_rate(self) -> float:
        """Percentage of cost saved"""
        if self.total_cost == 0:
            return 0.0
        return (self.cache_savings + self.optimization_savings) / self.total_cost


@dataclass(frozen=True)
class CostAttribution:
    """Attribution of costs to different dimensions"""

    request_id: UUID

    # Attribution dimensions
    user_id: Optional[str] = None
    feature_name: Optional[str] = None
    experiment_id: Optional[str] = None
    application: str = "default"

    # Cost breakdown
    cost_breakdown: CostBreakdown = field(
        default_factory=lambda: CostBreakdown(0, 0, 0, 0)
    )

    # Resource usage
    input_tokens: int = 0
    output_tokens: int = 0
    cache_hits: int = 0

    # Timing
    latency_ms: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CostMetrics:
    """Aggregated cost metrics"""

    period_start: datetime
    period_end: datetime

    # Total costs
    total_requests: int = 0
    total_cost_usd: float = 0.0
    total_savings_usd: float = 0.0

    # By dimension
    cost_by_user: Dict[str, float] = field(default_factory=dict)
    cost_by_feature: Dict[str, float] = field(default_factory=dict)
    cost_by_model: Dict[str, float] = field(default_factory=dict)

    # Efficiency metrics
    avg_cost_per_request: float = 0.0
    avg_cost_per_1k_tokens: float = 0.0
    cache_hit_rate: float = 0.0

    # Top cost drivers
    top_users: List[Dict[str, float]] = field(default_factory=list)
    top_features: List[Dict[str, float]] = field(default_factory=list)

    @property
    def savings_rate(self) -> float:
        """Overall savings rate"""
        denominator = self.total_cost_usd + self.total_savings_usd
        if denominator == 0:
            return 0.0
        return self.total_savings_usd / denominator


@dataclass(frozen=True)
class CostAlert:
    """Alert for cost anomalies"""

    id: UUID = field(default_factory=uuid4)

    # Alert details
    severity: str  # "info", "warning", "critical"
    title: str
    description: str

    # Cost information
    current_cost: float
    expected_cost: float
    variance: float

    # Attribution
    affected_users: List[str] = field(default_factory=list)
    affected_features: List[str] = field(default_factory=list)

    # Recommendations
    recommendations: List[str] = field(default_factory=list)

    timestamp: datetime = field(default_factory=datetime.utcnow)


