from __future__ import annotations

import pytest

from inference_engine.benchmarking.harness import summarize_traces
from inference_engine.benchmarking.sqlite_ledger import SQLiteBenchmarkLedger
from inference_engine.infrastructure.telemetry.request_log import RequestTrace, RouteTrace


def _trace(request_id: str = "request-1") -> RequestTrace:
    return RequestTrace(
        request_id=request_id,
        provider="openai",
        model="test-model",
        latency_ms=123,
        prompt_tokens=10,
        completion_tokens=5,
        total_tokens=15,
        estimated_cost_usd=0.001,
        pricing_table_version="test",
        cache_hit=False,
        error_type=None,
        error_message=None,
        timestamp="2026-01-01T00:00:00+00:00",
    )


def _route(request_id: str = "request-1") -> RouteTrace:
    return RouteTrace(
        request_id=request_id,
        strategy="single_model",
        selected_model="test-model",
        estimated_cost_usd=0.001,
        estimated_latency_ms=250,
        decision_reason="single model",
        considered_models=["test-model"],
        fallback_models=[],
        max_estimated_cost_usd=0.01,
        budget_violation=False,
        budget_violation_reason=None,
        timestamp="2026-01-01T00:00:00+00:00",
    )


def test_sqlite_benchmark_ledger_records_report_and_traces(tmp_path) -> None:
    ledger = SQLiteBenchmarkLedger(tmp_path / "benchmarks.sqlite3")
    traces = [_trace()]
    routes = [_route()]
    report = summarize_traces(
        workload_path=tmp_path / "workload.jsonl",
        strategy="single_model",
        provider="openai",
        model="test-model",
        ledger_path=tmp_path / "ledger.jsonl",
        traces=traces,
        route_traces=routes,
    )

    ledger.record_run(run_id="run-1", report=report, traces=traces, route_traces=routes)

    stored_report = ledger.get_report("run-1")
    stored_traces = ledger.get_traces("run-1")
    stored_routes = ledger.get_routes("run-1")
    assert stored_report.request_count == 1
    assert stored_report.route_count == 1
    assert stored_report.estimated_cost_usd == pytest.approx(0.001)
    assert stored_traces == traces
    assert stored_routes == routes


def test_sqlite_benchmark_ledger_replaces_existing_run(tmp_path) -> None:
    ledger = SQLiteBenchmarkLedger(tmp_path / "benchmarks.sqlite3")
    first_trace = _trace("request-1")
    second_trace = _trace("request-2")
    first_report = summarize_traces(
        workload_path=tmp_path / "workload.jsonl",
        strategy="single_model",
        provider="openai",
        model="test-model",
        ledger_path=tmp_path / "ledger.jsonl",
        traces=[first_trace],
    )
    second_report = summarize_traces(
        workload_path=tmp_path / "workload.jsonl",
        strategy="single_model",
        provider="openai",
        model="test-model",
        ledger_path=tmp_path / "ledger.jsonl",
        traces=[second_trace],
    )

    ledger.record_run(run_id="run-1", report=first_report, traces=[first_trace])
    ledger.record_run(run_id="run-1", report=second_report, traces=[second_trace])

    assert ledger.get_traces("run-1") == [second_trace]


def test_sqlite_benchmark_ledger_unknown_run_fails(tmp_path) -> None:
    ledger = SQLiteBenchmarkLedger(tmp_path / "benchmarks.sqlite3")

    with pytest.raises(KeyError, match="Unknown benchmark run_id"):
        ledger.get_report("missing")
