"""Unit tests for cost management."""
import pytest

from inference_engine.domain.models.routing import ModelConfig, ModelTier
from inference_engine.domain.models.cost import CostBreakdown
from inference_engine.domain.cost.calculator import CostCalculator


@pytest.fixture
def sample_model() -> ModelConfig:
    """Create sample model configuration."""
    return ModelConfig(
        id="test-model",
        name="Test Model",
        tier=ModelTier.STANDARD,
        max_context_length=2048,
        cost_per_1k_input_tokens=0.01,
        cost_per_1k_output_tokens=0.02,
    )


class TestCostCalculator:
    """Tests for CostCalculator."""

    def test_calculate_cost(self, sample_model):
        """Test cost calculation."""
        calculator = CostCalculator()
        
        cost = calculator.calculate(sample_model, input_tokens=100, output_tokens=50)
        
        # 100 input tokens at $0.01/1k = $0.001
        # 50 output tokens at $0.02/1k = $0.001
        # Total = $0.002
        expected = (100 / 1000) * 0.01 + (50 / 1000) * 0.02
        assert abs(cost - expected) < 0.0001

    def test_calculate_savings(self, sample_model):
        """Test savings calculation."""
        calculator = CostCalculator()
        
        premium_model = ModelConfig(
            id="premium",
            name="Premium",
            tier=ModelTier.PREMIUM,
            max_context_length=4096,
            cost_per_1k_input_tokens=0.05,
            cost_per_1k_output_tokens=0.10,
        )
        
        savings = calculator.calculate_savings(
            premium_model,
            sample_model,
            input_tokens=100,
            output_tokens=50,
        )
        
        assert savings > 0


class TestCostBreakdown:
    """Tests for CostBreakdown."""

    def test_savings_rate(self):
        """Test savings rate calculation."""
        breakdown = CostBreakdown(
            inference_cost=100.0,
            compute_cost=20.0,
            cache_savings=30.0,
            optimization_savings=50.0,
        )
        
        assert breakdown.savings_rate == 0.5  # 80 savings / 120 total

    def test_net_cost(self):
        """Test net cost calculation."""
        breakdown = CostBreakdown(
            inference_cost=100.0,
            compute_cost=20.0,
            cache_savings=30.0,
            optimization_savings=50.0,
        )
        
        assert breakdown.net_cost == 40.0  # 120 total - 80 savings

