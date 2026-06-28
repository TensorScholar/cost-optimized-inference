from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from uuid import UUID

from ...domain.cost.pricing import PRICING_TABLE_VERSION
from ...domain.models.response import InferenceResponse
from ...infrastructure.models.errors import ProviderError
from ...utils.time import utc_now


@dataclass(frozen=True)
class RequestTrace:
    """One append-only request execution record."""

    request_id: str
    provider: str
    model: str
    latency_ms: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    pricing_table_version: str
    cache_hit: bool
    error_type: str | None
    error_message: str | None
    timestamp: str
    quality_passed: bool | None = None
    quality_score: float | None = None
    quality_reason: str | None = None
    eval_type: str | None = None

    @classmethod
    def from_response(
        cls,
        *,
        provider: str,
        response: InferenceResponse,
        pricing_table_version: str = PRICING_TABLE_VERSION,
    ) -> RequestTrace:
        return cls(
            request_id=str(response.request_id),
            provider=provider,
            model=response.model_used,
            latency_ms=response.latency_ms,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            total_tokens=response.usage.total_tokens,
            estimated_cost_usd=response.usage.cost_usd,
            pricing_table_version=pricing_table_version,
            cache_hit=response.cache_info.hit,
            error_type=None,
            error_message=None,
            timestamp=response.timestamp.isoformat(),
        )

    @classmethod
    def from_error(
        cls,
        *,
        request_id: UUID,
        provider: str,
        model: str,
        latency_ms: int,
        error: ProviderError,
        pricing_table_version: str = PRICING_TABLE_VERSION,
    ) -> RequestTrace:
        return cls(
            request_id=str(request_id),
            provider=provider,
            model=model,
            latency_ms=latency_ms,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            estimated_cost_usd=0.0,
            pricing_table_version=pricing_table_version,
            cache_hit=False,
            error_type=error.error_type.value,
            error_message=error.message,
            timestamp=utc_now().isoformat(),
        )


class JsonlRequestLog:
    """Append-only JSONL request ledger for local smoke and benchmark runs."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def append(self, trace: RequestTrace) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(trace), sort_keys=True) + "\n")

    def read_all(self) -> list[RequestTrace]:
        if not self.path.exists():
            return []

        traces: list[RequestTrace] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                traces.append(RequestTrace(**json.loads(line)))
        return traces
