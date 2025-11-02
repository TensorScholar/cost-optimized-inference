from typing import Dict, Optional
import structlog

from ..models.routing import ModelConfig

logger = structlog.get_logger()


class CostCalculator:
    """Calculates costs for LLM inference requests."""

    def __init__(self, pricing_table: Optional[Dict[str, Dict[str, float]]] = None):
        self.pricing_table = pricing_table or self._default_pricing()

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

    def _default_pricing(self) -> Dict[str, Dict[str, float]]:
        """Default pricing table for common models."""
        return {
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
            "claude-3-opus": {"input": 0.015, "output": 0.075},
            "claude-3-sonnet": {"input": 0.003, "output": 0.015},
        }

