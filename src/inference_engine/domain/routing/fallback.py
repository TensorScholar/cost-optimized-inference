from typing import List, Optional
import structlog

from ..models.request import InferenceRequest
from ..models.routing import ModelConfig, RoutingDecision


logger = structlog.get_logger()


class FallbackChain:
    """
    Manages fallback chain for model routing.

    Tries primary model, falls back to alternatives on failure.
    """

    def __init__(
        self, primary: ModelConfig, fallbacks: List[ModelConfig], max_attempts: int = 3
    ):
        self.primary = primary
        self.fallbacks = fallbacks
        self.max_attempts = max_attempts
        self.attempt_count = 0

    def get_next_model(self) -> Optional[ModelConfig]:
        """Get next model in fallback chain."""
        if self.attempt_count >= self.max_attempts:
            return None

        if self.attempt_count == 0:
            model = self.primary
        else:
            fallback_index = (self.attempt_count - 1) % len(self.fallbacks)
            model = self.fallbacks[fallback_index]

        self.attempt_count += 1
        return model

    def reset(self) -> None:
        """Reset attempt counter."""
        self.attempt_count = 0

    def has_more_attempts(self) -> bool:
        """Check if more fallback attempts are available."""
        return self.attempt_count < self.max_attempts

