
import structlog

from ..models.routing import ModelConfig
from .pricing import PricingTable

logger = structlog.get_logger()


class CostCalculator:
    """Calculates costs for LLM inference requests."""

    def __init__(self, pricing_table: PricingTable | None = None) -> None:
        self.pricing_table = pricing_table or PricingTable()

    def calculate(
        self, model: ModelConfig, input_tokens: int, output_tokens: int
    ) -> float:
        """
        Calculate cost for inference.

        Args:
            model: Model configuration
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Total cost in USD
        """
        input_cost = (input_tokens / 1000) * model.cost_per_1k_input_tokens
        output_cost = (output_tokens / 1000) * model.cost_per_1k_output_tokens
        total = input_cost + output_cost

        logger.debug(
            "cost_calculated",
            model=model.id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_cost=total,
        )

        return total

    def calculate_for_model_name(
        self,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
        cached_input_tokens: int = 0,
    ) -> float:
        """Calculate cost from provider usage metadata and a versioned pricing table."""
        total = self.pricing_table.calculate(
            model=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_input_tokens=cached_input_tokens,
        )

        logger.debug(
            "cost_calculated_from_provider_usage",
            model=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_input_tokens=cached_input_tokens,
            pricing_table_version=self.pricing_table.version,
            total_cost=total,
        )
        return total

    def calculate_savings(
        self,
        base_model: ModelConfig,
        alternative_model: ModelConfig,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """
        Calculate cost savings from using alternative model.

        Returns:
            Cost savings in USD
        """
        base_cost = self.calculate(base_model, input_tokens, output_tokens)
        alt_cost = self.calculate(alternative_model, input_tokens, output_tokens)
        return max(0, base_cost - alt_cost)

