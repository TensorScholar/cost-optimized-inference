from dataclasses import dataclass
from typing import List
from .inference_dto import InferenceInputDTO, InferenceOutputDTO


@dataclass(frozen=True)
class BatchInputDTO:
    requests: List[InferenceInputDTO]


@dataclass(frozen=True)
class BatchOutputDTO:
    responses: List[InferenceOutputDTO]
