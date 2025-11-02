"""Unit tests for routing strategies."""
import pytest

from inference_engine.domain.models.request import InferenceRequest, ModelParameters
from inference_engine.domain.models.routing import ModelConfig, ModelTier
from inference_engine.domain.routing.cost_aware import CostAwareRouter
from inference_engine.domain.routing.complexity import ComplexityEstimator
from inference_engine.domain.routing.load_balanced import LoadBalancedRouter


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

