from __future__ import annotations

from uuid import uuid4

from inference_engine.domain.models.response import CacheInfo, InferenceResponse, UsageMetrics
from inference_engine.domain.models.routing import (
    ModelConfig,
    ModelTier,
    RoutingDecision,
    RoutingStrategy,
)
from inference_engine.infrastructure.models.errors import ProviderError, ProviderErrorType
from inference_engine.infrastructure.telemetry.request_log import (
    JsonlRequestLog,
    JsonlRouteLog,
    RequestTrace,
    RouteTrace,
)


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
        provider_attempt_count=3,
        provider_retry_count=2,
    )
    request_log = JsonlRequestLog(tmp_path / "ledger.jsonl")

    request_log.append(RequestTrace.from_response(provider="openai", response=response))

    traces = request_log.read_all()
    assert len(traces) == 1
    assert traces[0].request_id == str(response.request_id)
    assert traces[0].model == "test-model"
    assert traces[0].estimated_cost_usd == 0.00002
    assert traces[0].error_type is None
    assert traces[0].provider_attempt_count == 3
    assert traces[0].provider_retry_count == 2


def test_jsonl_request_log_round_trips_error_trace(tmp_path) -> None:
    request_id = uuid4()
    request_log = JsonlRequestLog(tmp_path / "ledger.jsonl")
    error = ProviderError(
        ProviderErrorType.RATE_LIMIT,
        "rate limited",
        provider="openai-compatible",
        retryable=True,
        status_code=429,
        provider_attempt_count=2,
        provider_retry_count=1,
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
    assert traces[0].provider_attempt_count == 2
    assert traces[0].provider_retry_count == 1


def test_jsonl_route_log_round_trips_route_trace(tmp_path) -> None:
    request_id = uuid4()
    model = ModelConfig(
        id="test-model",
        name="Test Model",
        tier=ModelTier.STANDARD,
        max_context_length=4096,
    )
    decision = RoutingDecision(
        request_id=request_id,
        selected_model=model,
        strategy=RoutingStrategy.SINGLE_MODEL,
        complexity_estimate=None,
        estimated_cost=0.001,
        estimated_latency_ms=250,
        estimated_quality_score=0.7,
        decision_reason="test route",
        fallback_models=[],
        considered_models=["test-model"],
    )
    route_log = JsonlRouteLog(tmp_path / "routes.jsonl")

    route_log.append(
        RouteTrace.from_decision(
            decision,
            max_estimated_cost_usd=0.0005,
            budget_violation_reason="too expensive",
        )
    )

    traces = route_log.read_all()
    assert len(traces) == 1
    assert traces[0].request_id == str(request_id)
    assert traces[0].selected_model == "test-model"
    assert traces[0].budget_violation is True
    assert traces[0].budget_violation_reason == "too expensive"
