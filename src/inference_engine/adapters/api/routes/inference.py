from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import uuid4

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
async def create_inference(request: InferenceRequestDTO) -> InferenceResponseDTO:
    # Minimal stub: echo-like behavior to enable API bring-up
    fake_tokens = max(len(request.prompt) // 4, 1)
    return InferenceResponseDTO(
        id=str(uuid4()),
        text=f"Echo: {request.prompt[:200]}",
        model_used="economy-dummy",
        tokens_used=fake_tokens,
        cost_usd=round(fake_tokens * 0.002 / 1000, 8),
        latency_ms=20,
        cache_hit=False,
    )


@router.post("/batch", response_model=List[InferenceResponseDTO])
async def create_batch_inference(requests: List[InferenceRequestDTO]) -> List[InferenceResponseDTO]:
    responses: List[InferenceResponseDTO] = []
    for req in requests:
        responses.append(
            await create_inference(req)  # reuse stub logic
        )
    return responses


