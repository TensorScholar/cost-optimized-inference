"""Model management API routes."""
from fastapi import APIRouter, Depends
from typing import List, Dict
from pydantic import BaseModel

from ..dependencies import get_routing_service
from ....application.services.routing.routing_service import RoutingService

router = APIRouter()


class ModelInfoDTO(BaseModel):
    id: str
    name: str
    tier: str
    max_context_length: int
    supports_streaming: bool
    supports_batching: bool
    cost_per_1k_input: float
    cost_per_1k_output: float
    healthy: bool
    current_load: float


@router.get("/models", response_model=List[ModelInfoDTO])
async def list_models(
    routing_service: RoutingService = Depends(get_routing_service),
) -> List[ModelInfoDTO]:
    """List available models and their configurations."""
    # For now, return mock data
    # In production, this would query the model pool
    return [
        ModelInfoDTO(
            id="gpt-4",
            name="GPT-4",
            tier="premium",
            max_context_length=8192,
            supports_streaming=True,
            supports_batching=True,
            cost_per_1k_input=0.03,
            cost_per_1k_output=0.06,
            healthy=True,
            current_load=0.0,
        ),
        ModelInfoDTO(
            id="gpt-3.5-turbo",
            name="GPT-3.5 Turbo",
            tier="economy",
            max_context_length=4096,
            supports_streaming=True,
            supports_batching=True,
            cost_per_1k_input=0.0015,
            cost_per_1k_output=0.002,
            healthy=True,
            current_load=0.0,
        ),
    ]

