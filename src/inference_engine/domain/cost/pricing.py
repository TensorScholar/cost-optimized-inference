from __future__ import annotations

from dataclasses import dataclass

PRICING_TABLE_VERSION = "2026-06-30"


@dataclass(frozen=True)
class ModelPricing:
    """USD pricing per one million tokens."""

    model: str
    input_per_million: float
    output_per_million: float
    cached_input_per_million: float | None = None


DEFAULT_PRICING: dict[str, ModelPricing] = {
    "gpt-4o-mini": ModelPricing(
        model="gpt-4o-mini",
        input_per_million=0.15,
        output_per_million=0.60,
        cached_input_per_million=0.075,
    ),
    "gpt-4o": ModelPricing(
        model="gpt-4o",
        input_per_million=2.50,
        output_per_million=10.00,
        cached_input_per_million=1.25,
    ),
    "gpt-3.5-turbo": ModelPricing(
        model="gpt-3.5-turbo",
        input_per_million=0.50,
        output_per_million=1.50,
    ),
    "gpt-5.5": ModelPricing(
        model="gpt-5.5",
        input_per_million=5.00,
        output_per_million=30.00,
        cached_input_per_million=0.50,
    ),
    "gpt-5.4": ModelPricing(
        model="gpt-5.4",
        input_per_million=2.50,
        output_per_million=15.00,
        cached_input_per_million=0.25,
    ),
    "gpt-5.4-mini": ModelPricing(
        model="gpt-5.4-mini",
        input_per_million=0.75,
        output_per_million=4.50,
        cached_input_per_million=0.075,
    ),
    "gpt-5.3-codex": ModelPricing(
        model="gpt-5.3-codex",
        input_per_million=1.75,
        output_per_million=14.00,
        cached_input_per_million=0.175,
    ),
}


class UnknownModelPricingError(ValueError):
    """Raised when cost is requested for a model missing from the pricing table."""


class PricingTable:
    """Versioned pricing lookup for benchmark and runtime cost accounting."""

    def __init__(
        self,
        prices: dict[str, ModelPricing] | None = None,
        version: str = PRICING_TABLE_VERSION,
    ) -> None:
        self.prices = prices or DEFAULT_PRICING
        self.version = version

    def get(self, model: str) -> ModelPricing:
        try:
            return self.prices[model]
        except KeyError as exc:
            raise UnknownModelPricingError(
                f"Missing pricing for model '{model}' in pricing table {self.version}"
            ) from exc

    def calculate(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cached_input_tokens: int = 0,
    ) -> float:
        pricing = self.get(model)
        billable_input_tokens = max(input_tokens - cached_input_tokens, 0)
        input_cost = billable_input_tokens * pricing.input_per_million / 1_000_000
        cached_rate = pricing.cached_input_per_million
        cached_cost = (
            cached_input_tokens * cached_rate / 1_000_000
            if cached_rate is not None
            else cached_input_tokens * pricing.input_per_million / 1_000_000
        )
        output_cost = output_tokens * pricing.output_per_million / 1_000_000
        return input_cost + cached_cost + output_cost
