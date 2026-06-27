"""Unit tests for cost management."""
import pytest

from inference_engine.domain.cost.calculator import CostCalculator
from inference_engine.domain.cost.pricing import (
    ModelPricing,
    PricingTable,
    UnknownModelPricingError,
)
from inference_engine.domain.models.cost import CostBreakdown
from inference_engine.domain.models.routing import ModelConfig, ModelTier


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

    def test_calculate_for_model_name_uses_versioned_pricing(self):
        """Test provider usage cost calculation from model pricing."""
        calculator = CostCalculator(
            PricingTable(
                prices={
                    "test-model": ModelPricing(
                        model="test-model",
                        input_per_million=1.00,
                        output_per_million=2.00,
                    )
                },
                version="test",
            )
        )

        cost = calculator.calculate_for_model_name(
            "test-model",
            input_tokens=1_000,
            output_tokens=500,
        )

        assert cost == pytest.approx(0.002)

    def test_calculate_for_model_name_uses_cached_input_rate(self):
        """Test cached input tokens are priced separately when available."""
        calculator = CostCalculator(
            PricingTable(
                prices={
                    "test-model": ModelPricing(
                        model="test-model",
                        input_per_million=1.00,
                        output_per_million=2.00,
                        cached_input_per_million=0.25,
                    )
                },
                version="test",
            )
        )

        cost = calculator.calculate_for_model_name(
            "test-model",
            input_tokens=1_000,
            output_tokens=500,
            cached_input_tokens=400,
        )

        assert cost == pytest.approx(0.0017)

    def test_calculate_for_model_name_fails_unknown_pricing(self):
        """Test unknown model pricing fails instead of silently returning fake cost."""
        calculator = CostCalculator(PricingTable(prices={}, version="test"))

        with pytest.raises(UnknownModelPricingError):
            calculator.calculate_for_model_name(
                "missing-model",
                input_tokens=1,
                output_tokens=1,
            )


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

        assert breakdown.savings_rate == pytest.approx(80 / 120)

    def test_net_cost(self):
        """Test net cost calculation."""
        breakdown = CostBreakdown(
            inference_cost=100.0,
            compute_cost=20.0,
            cache_savings=30.0,
            optimization_savings=50.0,
        )

        assert breakdown.net_cost == 40.0  # 120 total - 80 savings
