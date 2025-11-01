from dataclasses import dataclass


@dataclass(frozen=True)
class InferenceInputDTO:
    prompt: str
    max_tokens: int
    temperature: float


@dataclass(frozen=True)
class InferenceOutputDTO:
    text: str
    model_used: str
    tokens_used: int
    cost_usd: float
    latency_ms: int
    cache_hit: bool
