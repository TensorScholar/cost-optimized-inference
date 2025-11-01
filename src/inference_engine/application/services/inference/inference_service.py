from dataclasses import dataclass
from ...dto.inference_dto import InferenceInputDTO, InferenceOutputDTO
from ...dto.metrics_dto import RequestMetricsDTO
from ...utils.text_utils import estimate_tokens


@dataclass
class InferenceService:
    async def infer(self, dto: InferenceInputDTO) -> InferenceOutputDTO:
        tokens = estimate_tokens(dto.prompt)
        return InferenceOutputDTO(
            text=f"Echo: {dto.prompt[:200]}",
            model_used="economy-dummy",
            tokens_used=tokens,
            cost_usd=round(tokens * 0.002 / 1000, 8),
            latency_ms=20,
            cache_hit=False,
        )
