from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import uuid4

from ..dependencies import get_inference_service, get_batch_service
from ....application.services.inference.inference_service import InferenceService
from ....application.services.inference.batch_service import BatchService

router = APIRouter()


class InferenceRequestDTO(BaseModel):
    prompt: str
    max_tokens: int = Field(default=1024, ge=1)
    temperature: float = Field(default=0.7, ge=0, le=2)
    priority: str = Field(default="standard")
    use_cache: bool = True


class InferenceResponseDTO(BaseModel):
    id: str
    text: str
    model_used: str
    tokens_used: int
    cost_usd: float
    latency_ms: int
    cache_hit: bool


@router.post("/inference", response_model=InferenceResponseDTO)
async def create_inference(
    request: InferenceRequestDTO,
    inference_service: InferenceService = Depends(get_inference_service),
) -> InferenceResponseDTO:
    """Process single inference request."""
    from ....application.dto.inference_dto import InferenceInputDTO
    
    input_dto = InferenceInputDTO(
        prompt=request.prompt,
        max_tokens=request.max_tokens,
        temperature=request.temperature,
    )
    
    output_dto = await inference_service.infer(input_dto)
    
    return InferenceResponseDTO(
        id=str(uuid4()),
        text=output_dto.text,
        model_used=output_dto.model_used,
        tokens_used=output_dto.tokens_used,
        cost_usd=output_dto.cost_usd,
        latency_ms=output_dto.latency_ms,
        cache_hit=output_dto.cache_hit,
    )


@router.post("/batch", response_model=List[InferenceResponseDTO])
async def create_batch_inference(
    requests: List[InferenceRequestDTO],
    batch_service: BatchService = Depends(get_batch_service),
) -> List[InferenceResponseDTO]:
    """Process batch inference requests."""
    from ....application.dto.batch_dto import BatchInputDTO
    from ....application.dto.inference_dto import InferenceInputDTO
    
    input_dtos = [
        InferenceInputDTO(
            prompt=req.prompt,
            max_tokens=req.max_tokens,
            temperature=req.temperature,
        )
        for req in requests
    ]
    
    batch_input = BatchInputDTO(requests=input_dtos)
    batch_output = await batch_service.process_batch(batch_input)
    
    return [
        InferenceResponseDTO(
            id=str(uuid4()),
            text=resp.text,
            model_used=resp.model_used,
            tokens_used=resp.tokens_used,
            cost_usd=resp.cost_usd,
            latency_ms=resp.latency_ms,
            cache_hit=resp.cache_hit,
        )
        for resp in batch_output.responses
    ]


