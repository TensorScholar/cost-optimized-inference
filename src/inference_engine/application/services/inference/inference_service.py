"""Inference service for processing single requests."""
from ...dto.inference_dto import InferenceInputDTO, InferenceOutputDTO
from ...utils.text_utils import estimate_tokens


class InferenceService:
    """Service for processing single inference requests."""

    async def infer(self, dto: InferenceInputDTO) -> InferenceOutputDTO:
        """
        Process inference request.

        Args:
            dto: Inference input DTO

        Returns:
            Inference output DTO with generated text and metadata
        """
        tokens = estimate_tokens(dto.prompt)
        return InferenceOutputDTO(
            text=f"Echo: {dto.prompt[:200]}",
            model_used="economy-dummy",
            tokens_used=tokens,
            cost_usd=round(tokens * 0.002 / 1000, 8),
            latency_ms=20,
            cache_hit=False,
        )
