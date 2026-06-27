from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path
from time import perf_counter

from inference_engine.benchmarking.harness import load_workload, summarize_traces, write_report
from inference_engine.domain.cost.pricing import DEFAULT_PRICING, UnknownModelPricingError
from inference_engine.domain.models.request import InferenceRequest, ModelParameters
from inference_engine.domain.models.routing import ModelConfig, ModelTier, RoutingStrategy
from inference_engine.domain.routing.baseline import BaselineRouter
from inference_engine.domain.routing.complexity import ComplexityEstimator
from inference_engine.infrastructure.models.errors import ProviderError, classify_openai_error
from inference_engine.infrastructure.models.openai_backend import OpenAIBackend, RetryPolicy
from inference_engine.infrastructure.telemetry.request_log import JsonlRequestLog, RequestTrace


def main() -> int:
    parser = argparse.ArgumentParser(prog="run_benchmark")
    parser.add_argument("--workload", default="benchmarks/workloads/smoke.jsonl")
    parser.add_argument("--provider", choices=["openai"], default="openai")
    parser.add_argument("--model", default="gpt-4o-mini")
    parser.add_argument("--strategy", choices=["single_model", "rule_based"], default="single_model")
    parser.add_argument("--economy-model", default="gpt-4o-mini")
    parser.add_argument("--standard-model", default="gpt-4o-mini")
    parser.add_argument("--premium-model", default="gpt-4o")
    parser.add_argument("--base-url", default=os.getenv("OPENAI_BASE_URL"))
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    parser.add_argument("--max-tokens", type=int, default=128)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--ledger-path", default="reports/benchmarks/latest-ledger.jsonl")
    parser.add_argument("--report-path", default="reports/benchmarks/latest-report.json")
    args = parser.parse_args()
    return asyncio.run(_run(args))


async def _run(args: argparse.Namespace) -> int:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY is required for provider=openai")
        return 2

    workload_path = Path(args.workload)
    ledger_path = Path(args.ledger_path)
    report_path = Path(args.report_path)
    workload = load_workload(workload_path)
    request_log = JsonlRequestLog(ledger_path)
    router = _build_router(args)
    backends: dict[str, OpenAIBackend] = {}

    def backend_for(model_name: str) -> OpenAIBackend:
        if model_name not in backends:
            backends[model_name] = OpenAIBackend(
                api_key=api_key,
                model_name=model_name,
                base_url=args.base_url,
                timeout_seconds=args.timeout_seconds,
                retry_policy=RetryPolicy(max_attempts=2),
            )
        return backends[model_name]

    report_model = (
        args.model
        if args.strategy == RoutingStrategy.SINGLE_MODEL.value
        else ",".join([args.economy_model, args.standard_model, args.premium_model])
    )

    traces: list[RequestTrace] = []
    for item in workload:
        request = InferenceRequest(
            prompt=item.prompt,
            parameters=ModelParameters(
                max_tokens=args.max_tokens,
                temperature=args.temperature,
            ),
        )
        decision = await router.route(request)
        selected_model = decision.selected_model.id
        started = perf_counter()
        try:
            response = await backend_for(selected_model).infer(request)
            trace = RequestTrace.from_response(provider=args.provider, response=response)
        except ProviderError as exc:
            trace = RequestTrace.from_error(
                request_id=request.id,
                provider=args.provider,
                model=selected_model,
                latency_ms=int((perf_counter() - started) * 1000),
                error=exc,
            )
        except Exception as exc:
            trace = RequestTrace.from_error(
                request_id=request.id,
                provider=args.provider,
                model=selected_model,
                latency_ms=int((perf_counter() - started) * 1000),
                error=classify_openai_error(exc),
            )
        request_log.append(trace)
        traces.append(trace)

    report = summarize_traces(
        workload_path=workload_path,
        strategy=args.strategy,
        provider=args.provider,
        model=report_model,
        ledger_path=ledger_path,
        traces=traces,
    )
    write_report(report, report_path)
    print(
        " ".join(
            [
                f"requests={report.request_count}",
                f"successes={report.success_count}",
                f"failures={report.failure_count}",
                f"latency_p50_ms={report.latency_p50_ms}",
                f"latency_p95_ms={report.latency_p95_ms}",
                f"estimated_cost_usd={report.estimated_cost_usd:.8f}",
                f"report_path={report_path}",
            ]
        )
    )
    return 0 if report.failure_count == 0 else 1


def _build_router(args: argparse.Namespace) -> BaselineRouter:
    strategy = RoutingStrategy(args.strategy)
    if strategy == RoutingStrategy.SINGLE_MODEL:
        return BaselineRouter(
            [_model_config(args.model, ModelTier.STANDARD)],
            ComplexityEstimator(),
            mode=strategy,
            single_model_id=args.model,
        )

    models = [
        _model_config(args.economy_model, ModelTier.ECONOMY),
        _model_config(args.standard_model, ModelTier.STANDARD),
        _model_config(args.premium_model, ModelTier.PREMIUM),
    ]
    return BaselineRouter(
        models,
        ComplexityEstimator(),
        mode=strategy,
        single_model_id=args.model if strategy == RoutingStrategy.SINGLE_MODEL else None,
    )


def _model_config(model_name: str, tier: ModelTier) -> ModelConfig:
    try:
        pricing = DEFAULT_PRICING[model_name]
    except KeyError as exc:
        raise UnknownModelPricingError(
            f"Benchmark model '{model_name}' is missing from the pricing table"
        ) from exc
    return ModelConfig(
        id=model_name,
        name=model_name,
        tier=tier,
        max_context_length=128_000,
        cost_per_1k_input_tokens=pricing.input_per_million / 1000,
        cost_per_1k_output_tokens=pricing.output_per_million / 1000,
    )


if __name__ == "__main__":
    raise SystemExit(main())
