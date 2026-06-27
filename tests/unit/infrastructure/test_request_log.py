from __future__ import annotations

from uuid import uuid4

from inference_engine.domain.models.response import CacheInfo, InferenceResponse, UsageMetrics
from inference_engine.infrastructure.models.errors import ProviderError, ProviderErrorType
from inference_engine.infrastructure.telemetry.request_log import JsonlRequestLog, RequestTrace


def test_jsonl_request_log_round_trips_success_trace(tmp_path) -> None:
    response = InferenceResponse(
        request_id=uuid4(),
        text="ok",
        model_used="test-model",
        usage=UsageMetrics(
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
            cost_usd=0.00002,
        ),
        cache_info=CacheInfo(hit=False),
        latency_ms=123,
    )
    request_log = JsonlRequestLog(tmp_path / "ledger.jsonl")

    request_log.append(RequestTrace.from_response(provider="openai", response=response))

    traces = request_log.read_all()
    assert len(traces) == 1
    assert traces[0].request_id == str(response.request_id)
    assert traces[0].model == "test-model"
    assert traces[0].estimated_cost_usd == 0.00002
    assert traces[0].error_type is None


def test_jsonl_request_log_round_trips_error_trace(tmp_path) -> None:
    request_id = uuid4()
    request_log = JsonlRequestLog(tmp_path / "ledger.jsonl")
    error = ProviderError(
        ProviderErrorType.RATE_LIMIT,
        "rate limited",
        provider="openai-compatible",
        retryable=True,
        status_code=429,
    )

    request_log.append(
        RequestTrace.from_error(
            request_id=request_id,
            provider="openai",
            model="test-model",
            latency_ms=42,
            error=error,
        )
    )

    traces = request_log.read_all()
    assert len(traces) == 1
    assert traces[0].request_id == str(request_id)
    assert traces[0].latency_ms == 42
    assert traces[0].error_type == "rate_limit"
    assert traces[0].estimated_cost_usd == 0.0
