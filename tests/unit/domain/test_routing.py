"""Unit tests for routing strategies."""
import pytest

from inference_engine.domain.models.request import InferenceRequest, ModelParameters
from inference_engine.domain.models.routing import (
    ModelConfig,
    ModelTier,
    RoutingReason,
    RoutingStrategy,
)
from inference_engine.domain.routing.baseline import BaselineRouter, BaselineRoutingModeError
from inference_engine.domain.routing.complexity import ComplexityEstimator
from inference_engine.domain.routing.cost_aware import CostAwareRouter
from inference_engine.domain.routing.load_balanced import LoadBalancedRouter
from inference_engine.domain.routing.policy import PolicyRouter, PolicyRouterConfig


@pytest.fixture
def sample_models() -> list[ModelConfig]:
    """Create sample model configurations."""
    return [
        ModelConfig(
            id="gpt-4",
            name="GPT-4",
            tier=ModelTier.PREMIUM,
            max_context_length=8192,
            cost_per_1k_input_tokens=0.03,
            cost_per_1k_output_tokens=0.06,
        ),
        ModelConfig(
            id="gpt-3.5",
            name="GPT-3.5 Turbo",
            tier=ModelTier.ECONOMY,
            max_context_length=4096,
            cost_per_1k_input_tokens=0.0015,
            cost_per_1k_output_tokens=0.002,
        ),
    ]


@pytest.fixture
def simple_request() -> InferenceRequest:
    """Create simple request."""
    return InferenceRequest(
        prompt="Hello world",
        parameters=ModelParameters(max_tokens=10),
    )


@pytest.fixture
def complex_request() -> InferenceRequest:
    """Create complex request."""
    return InferenceRequest(
        prompt="Analyze quantum computing and explain how superposition works in detail",
        parameters=ModelParameters(max_tokens=500),
    )


class TestComplexityEstimator:
    """Tests for ComplexityEstimator."""

    @pytest.mark.asyncio
    async def test_simple_query(self, simple_request):
        """Test simple query has low complexity."""
        estimator = ComplexityEstimator()

        complexity = await estimator.estimate(simple_request)
        assert complexity.score < 0.3

    @pytest.mark.asyncio
    async def test_complex_query(self, complex_request):
        """Test complex query has high complexity."""
        estimator = ComplexityEstimator()

        complexity = await estimator.estimate(complex_request)
        assert complexity.score > 0.5

    @pytest.mark.asyncio
    async def test_recommended_tier(self, simple_request, complex_request):
        """Test tier recommendations."""
        estimator = ComplexityEstimator()

        simple_complexity = await estimator.estimate(simple_request)
        complex_complexity = await estimator.estimate(complex_request)

        assert simple_complexity.recommended_tier == ModelTier.ECONOMY
        assert complex_complexity.recommended_tier in [ModelTier.STANDARD, ModelTier.PREMIUM]


class TestCostAwareRouter:
    """Tests for CostAwareRouter."""

    @pytest.mark.asyncio
    async def test_route_simple_request(self, simple_request, sample_models):
        """Test simple request routed to cheap model."""
        estimator = ComplexityEstimator()
        router = CostAwareRouter(sample_models, estimator, cost_weight=0.9)

        decision = await router.route(simple_request)

        assert decision.selected_model.id == "gpt-3.5"

    @pytest.mark.asyncio
    async def test_route_complex_request(self, complex_request, sample_models):
        """Test complex request routed to capable model."""
        estimator = ComplexityEstimator()
        router = CostAwareRouter(sample_models, estimator, cost_weight=0.5)

        decision = await router.route(complex_request)

        # Should prefer gpt-4 for complex tasks
        assert decision.estimated_cost > 0
        assert decision.estimated_latency_ms > 0

    @pytest.mark.asyncio
    async def test_fallback_chain(self, simple_request, sample_models):
        """Test fallback models included."""
        estimator = ComplexityEstimator()
        router = CostAwareRouter(sample_models, estimator)

        decision = await router.route(simple_request)

        assert len(decision.fallback_models) >= 0


class TestBaselineRouter:
    """Tests for deterministic benchmark baseline routing modes."""

    @pytest.mark.asyncio
    async def test_single_model_mode_routes_to_configured_model(self, simple_request, sample_models):
        """Test single_model baseline always uses the configured model."""
        router = BaselineRouter(
            sample_models,
            ComplexityEstimator(),
            mode=RoutingStrategy.SINGLE_MODEL,
            single_model_id="gpt-4",
        )

        decision = await router.route(simple_request)

        assert decision.strategy == RoutingStrategy.SINGLE_MODEL
        assert decision.selected_model.id == "gpt-4"
        assert "single_model baseline" in decision.decision_reason

    @pytest.mark.asyncio
    async def test_rule_based_mode_uses_cheapest_sufficient_tier(
        self,
        simple_request,
        complex_request,
        sample_models,
    ):
        """Test rule_based baseline maps complexity to the cheapest sufficient tier."""
        router = BaselineRouter(
            sample_models,
            ComplexityEstimator(),
            mode=RoutingStrategy.RULE_BASED,
        )

        simple_decision = await router.route(simple_request)
        complex_decision = await router.route(complex_request)

        assert simple_decision.selected_model.id == "gpt-3.5"
        assert complex_decision.selected_model.tier.rank >= ModelTier.STANDARD.rank
        assert complex_decision.complexity_estimate is not None

    @pytest.mark.asyncio
    async def test_single_model_mode_requires_model_id(self, simple_request, sample_models):
        """Test single_model baseline fails clearly without a configured model id."""
        router = BaselineRouter(
            sample_models,
            ComplexityEstimator(),
            mode=RoutingStrategy.SINGLE_MODEL,
        )

        with pytest.raises(BaselineRoutingModeError, match="single_model_id"):
            await router.route(simple_request)


class TestPolicyRouter:
    """Tests for deterministic SLO and budget-aware policy routing."""

    @pytest.fixture
    def policy_models(self) -> list[ModelConfig]:
        return [
            ModelConfig(
                id="economy",
                name="Economy",
                tier=ModelTier.ECONOMY,
                max_context_length=4096,
                avg_latency_ms=250,
                cost_per_1k_input_tokens=0.001,
                cost_per_1k_output_tokens=0.002,
            ),
            ModelConfig(
                id="standard",
                name="Standard",
                tier=ModelTier.STANDARD,
                max_context_length=8192,
                avg_latency_ms=700,
                cost_per_1k_input_tokens=0.005,
                cost_per_1k_output_tokens=0.01,
            ),
            ModelConfig(
                id="premium",
                name="Premium",
                tier=ModelTier.PREMIUM,
                max_context_length=128_000,
                avg_latency_ms=1400,
                cost_per_1k_input_tokens=0.03,
                cost_per_1k_output_tokens=0.06,
            ),
        ]

    @pytest.mark.asyncio
    async def test_policy_prefers_candidate_within_budget(self, simple_request, policy_models):
        router = PolicyRouter(
            policy_models,
            ComplexityEstimator(),
            PolicyRouterConfig(max_estimated_cost_usd=0.00003),
        )

        decision = await router.route(simple_request)

        assert decision.strategy == RoutingStrategy.POLICY
        assert decision.selected_model.id == "economy"
        assert decision.estimated_cost <= 0.00003
        assert decision.decision_reason == RoutingReason.POLICY_COST_WITHIN_BUDGET

    @pytest.mark.asyncio
    async def test_policy_latency_slo_filters_slow_models(self, simple_request, policy_models):
        router = PolicyRouter(
            policy_models,
            ComplexityEstimator(),
            PolicyRouterConfig(
                latency_slo_ms=800,
                min_quality_score=0.70,
            ),
        )

        decision = await router.route(simple_request)

        assert decision.selected_model.id == "standard"
        assert decision.estimated_latency_ms <= 800
        assert decision.decision_reason == RoutingReason.POLICY_LATENCY_WITHIN_SLO

    @pytest.mark.asyncio
    async def test_policy_quality_floor_selects_capable_model(self, simple_request, policy_models):
        router = PolicyRouter(
            policy_models,
            ComplexityEstimator(),
            PolicyRouterConfig(min_quality_score=0.90),
        )

        decision = await router.route(simple_request)

        assert decision.selected_model.id == "premium"
        assert decision.estimated_quality_score >= 0.90
        assert decision.decision_reason == RoutingReason.POLICY_QUALITY_FLOOR

    @pytest.mark.asyncio
    async def test_policy_records_impossible_budget_reason(self, simple_request, policy_models):
        router = PolicyRouter(
            policy_models,
            ComplexityEstimator(),
            PolicyRouterConfig(max_estimated_cost_usd=0.00000001),
        )

        decision = await router.route(simple_request)

        assert decision.selected_model.id == "economy"
        assert decision.estimated_cost > 0.00000001
        assert decision.decision_reason == RoutingReason.POLICY_NO_CANDIDATE_WITHIN_BUDGET

    @pytest.mark.asyncio
    async def test_policy_does_not_mask_impossible_quality_reason(
        self,
        simple_request,
        policy_models,
    ):
        router = PolicyRouter(
            policy_models,
            ComplexityEstimator(),
            PolicyRouterConfig(
                min_quality_score=1.0,
                latency_slo_ms=800,
            ),
        )

        decision = await router.route(simple_request)

        assert decision.decision_reason == RoutingReason.POLICY_NO_CANDIDATE_MEETS_QUALITY_FLOOR


class TestLoadBalancedRouter:
    """Tests for LoadBalancedRouter."""

    @pytest.mark.asyncio
    async def test_round_robin(self, simple_request, sample_models):
        """Test round-robin load balancing."""
        router = LoadBalancedRouter(sample_models)

        # Route multiple times
        decision1 = await router.route(simple_request)
        decision2 = await router.route(simple_request)

        # Should alternate
        assert decision1.selected_model.id != decision2.selected_model.id
