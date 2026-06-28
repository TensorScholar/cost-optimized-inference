from __future__ import annotations

import argparse
from uuid import uuid4

import pytest

import scripts.run_benchmark as benchmark_script
from inference_engine.cli import _run_smoke
from inference_engine.domain.models.routing import (
    ModelConfig,
    ModelTier,
    RoutingDecision,
    RoutingStrategy,
)
from inference_engine.domain.routing.policy import PolicyRouter


@pytest.mark.asyncio
async def test_smoke_cli_requires_openai_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    args = argparse.Namespace(
        provider="openai",
        model="gpt-4o-mini",
        prompt="hello",
        base_url=None,
        timeout_seconds=30.0,
        max_tokens=16,
        temperature=0.0,
        log_path="unused.jsonl",
    )

    exit_code = await _run_smoke(args)

    assert exit_code == 2


@pytest.mark.asyncio
async def test_benchmark_budget_violation_skips_provider_call(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    workload_path = tmp_path / "workload.jsonl"
    workload_path.write_text(
        '{"id":"one","prompt":"hello","eval":{"type":"contains_all","required":["hello"]}}\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    class FakeRouter:
        async def route(self, _request):
            model = ModelConfig(
                id="test-model",
                name="Test Model",
                tier=ModelTier.STANDARD,
                max_context_length=4096,
            )
            return RoutingDecision(
                request_id=uuid4(),
                selected_model=model,
                strategy=RoutingStrategy.SINGLE_MODEL,
                complexity_estimate=None,
                estimated_cost=0.02,
                estimated_latency_ms=100,
                estimated_quality_score=0.7,
                decision_reason="fake expensive route",
                fallback_models=[],
                considered_models=["test-model"],
            )

    class FailingBackend:
        def __init__(self, *args, **kwargs):
            raise AssertionError("provider backend should not be constructed")

    monkeypatch.setattr(benchmark_script, "_build_router", lambda _args: FakeRouter())
    monkeypatch.setattr(benchmark_script, "OpenAIBackend", FailingBackend)
    args = argparse.Namespace(
        provider="openai",
        model="test-model",
        strategy="single_model",
        economy_model="test-model",
        standard_model="test-model",
        premium_model="test-model",
        workload=str(workload_path),
        base_url=None,
        timeout_seconds=30.0,
        max_tokens=16,
        temperature=0.0,
        ledger_path=str(tmp_path / "ledger.jsonl"),
        route_ledger_path=str(tmp_path / "routes.jsonl"),
        sqlite_ledger_path=str(tmp_path / "ledger.sqlite3"),
        report_path=str(tmp_path / "report.json"),
        run_id="budget-test",
        max_estimated_cost_usd=0.001,
    )

    exit_code = await benchmark_script._run(args)

    assert exit_code == 1
    assert "budget_violation" in (tmp_path / "ledger.jsonl").read_text(encoding="utf-8")
    assert "fake expensive route" in (tmp_path / "routes.jsonl").read_text(encoding="utf-8")


def test_benchmark_build_router_supports_policy_strategy() -> None:
    args = argparse.Namespace(
        strategy="policy",
        model="gpt-4o-mini",
        economy_model="gpt-4o-mini",
        standard_model="gpt-4o-mini",
        premium_model="gpt-4o",
        max_estimated_cost_usd=0.002,
        policy_latency_slo_ms=800,
        policy_min_quality_score=0.70,
        policy_cost_weight=0.55,
        policy_latency_weight=0.25,
        policy_quality_weight=0.20,
    )

    router = benchmark_script._build_router(args)

    assert isinstance(router, PolicyRouter)
    assert router.config.max_estimated_cost_usd == 0.002
    assert router.config.latency_slo_ms == 800
    assert router.config.min_quality_score == 0.70
