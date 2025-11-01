from dataclasses import dataclass


@dataclass(frozen=True)
class RequestMetricsDTO:
    latency_ms: int
    prompt_tokens: int
    completion_tokens: int
    cache_hit: bool
    cost_usd: float
