from __future__ import annotations

import json
from argparse import Namespace

import pytest

from inference_engine.benchmarking.harness import (
    compare_reports,
    load_workload,
    summarize_traces,
    write_comparison,
    write_report,
)
from inference_engine.infrastructure.telemetry.request_log import RequestTrace
from scripts.run_benchmark import _compare


def test_load_workload_parses_jsonl(tmp_path) -> None:
    workload_path = tmp_path / "workload.jsonl"
    workload_path.write_text(
        '{"id":"one","prompt":"hello","tags":{"task":"smoke"}}\n',
        encoding="utf-8",
    )

    workload = load_workload(workload_path)

    assert len(workload) == 1
    assert workload[0].id == "one"
    assert workload[0].prompt == "hello"
    assert workload[0].tags == {"task": "smoke"}


def test_load_workload_rejects_empty_prompt(tmp_path) -> None:
    workload_path = tmp_path / "workload.jsonl"
    workload_path.write_text('{"id":"one","prompt":""}\n', encoding="utf-8")

    with pytest.raises(ValueError, match="missing string prompt"):
        load_workload(workload_path)


def test_summarize_traces_reports_latency_tokens_cost_and_failures(tmp_path) -> None:
    traces = [
        RequestTrace(
            request_id="1",
            provider="openai",
            model="test-model",
            latency_ms=100,
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
            estimated_cost_usd=0.01,
            pricing_table_version="test",
            cache_hit=False,
            error_type=None,
            error_message=None,
            timestamp="2026-01-01T00:00:00+00:00",
        ),
        RequestTrace(
            request_id="2",
            provider="openai",
            model="test-model",
            latency_ms=300,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            estimated_cost_usd=0.0,
            pricing_table_version="test",
            cache_hit=False,
            error_type="rate_limit",
            error_message="rate limited",
            timestamp="2026-01-01T00:00:01+00:00",
        ),
    ]

    report = summarize_traces(
        workload_path=tmp_path / "workload.jsonl",
        strategy="single_model",
        provider="openai",
        model="test-model",
        ledger_path=tmp_path / "ledger.jsonl",
        traces=traces,
    )

    assert report.request_count == 2
    assert report.success_count == 1
    assert report.failure_count == 1
    assert report.error_rate == 0.5
    assert report.latency_p50_ms == 100
    assert report.latency_p95_ms == 300
    assert report.prompt_tokens == 10
    assert report.completion_tokens == 5
    assert report.estimated_cost_usd == 0.01


def test_write_report_outputs_json(tmp_path) -> None:
    report = summarize_traces(
        workload_path=tmp_path / "workload.jsonl",
        strategy="single_model",
        provider="openai",
        model="test-model",
        ledger_path=tmp_path / "ledger.jsonl",
        traces=[],
    )
    report_path = tmp_path / "report.json"

    write_report(report, report_path)

    raw = json.loads(report_path.read_text(encoding="utf-8"))
    assert raw["request_count"] == 0
    assert raw["limitations"]


def test_compare_reports_marks_matching_runs_comparable(tmp_path) -> None:
    baseline = summarize_traces(
        workload_path=tmp_path / "workload.jsonl",
        strategy="single_model",
        provider="openai",
        model="baseline-model",
        ledger_path=tmp_path / "baseline.jsonl",
        traces=[
            RequestTrace(
                request_id="1",
                provider="openai",
                model="baseline-model",
                latency_ms=200,
                prompt_tokens=10,
                completion_tokens=10,
                total_tokens=20,
                estimated_cost_usd=0.04,
                pricing_table_version="test",
                cache_hit=False,
                error_type=None,
                error_message=None,
                timestamp="2026-01-01T00:00:00+00:00",
            )
        ],
    )
    candidate = summarize_traces(
        workload_path=tmp_path / "workload.jsonl",
        strategy="rule_based",
        provider="openai",
        model="candidate-model",
        ledger_path=tmp_path / "candidate.jsonl",
        traces=[
            RequestTrace(
                request_id="2",
                provider="openai",
                model="candidate-model",
                latency_ms=150,
                prompt_tokens=10,
                completion_tokens=10,
                total_tokens=20,
                estimated_cost_usd=0.02,
                pricing_table_version="test",
                cache_hit=False,
                error_type=None,
                error_message=None,
                timestamp="2026-01-01T00:00:00+00:00",
            )
        ],
    )

    comparison = compare_reports(
        baseline_run_id="baseline",
        baseline=baseline,
        candidate_run_id="candidate",
        candidate=candidate,
    )

    assert comparison.comparable is True
    assert comparison.cost_delta_usd == pytest.approx(-0.02)
    assert comparison.cost_delta_percent == pytest.approx(-50.0)
    assert comparison.latency_p95_delta_ms == -50


def test_compare_reports_rejects_different_request_counts(tmp_path) -> None:
    baseline = summarize_traces(
        workload_path=tmp_path / "workload.jsonl",
        strategy="single_model",
        provider="openai",
        model="baseline-model",
        ledger_path=tmp_path / "baseline.jsonl",
        traces=[
            RequestTrace(
                request_id="1",
                provider="openai",
                model="baseline-model",
                latency_ms=200,
                prompt_tokens=10,
                completion_tokens=10,
                total_tokens=20,
                estimated_cost_usd=0.04,
                pricing_table_version="test",
                cache_hit=False,
                error_type=None,
                error_message=None,
                timestamp="2026-01-01T00:00:00+00:00",
            )
        ],
    )
    candidate = summarize_traces(
        workload_path=tmp_path / "workload.jsonl",
        strategy="rule_based",
        provider="openai",
        model="candidate-model",
        ledger_path=tmp_path / "candidate.jsonl",
        traces=[],
    )

    comparison = compare_reports(
        baseline_run_id="baseline",
        baseline=baseline,
        candidate_run_id="candidate",
        candidate=candidate,
    )

    assert comparison.comparable is False
    assert any("request counts" in limitation for limitation in comparison.limitations)


def test_write_comparison_outputs_json(tmp_path) -> None:
    report = summarize_traces(
        workload_path=tmp_path / "workload.jsonl",
        strategy="single_model",
        provider="openai",
        model="test-model",
        ledger_path=tmp_path / "ledger.jsonl",
        traces=[],
    )
    comparison = compare_reports(
        baseline_run_id="baseline",
        baseline=report,
        candidate_run_id="candidate",
        candidate=report,
    )
    comparison_path = tmp_path / "comparison.json"

    write_comparison(comparison, comparison_path)

    raw = json.loads(comparison_path.read_text(encoding="utf-8"))
    assert raw["baseline_run_id"] == "baseline"
    assert raw["candidate_run_id"] == "candidate"
    assert raw["limitations"]


def test_compare_cli_writes_comparison_from_sqlite_ledger(tmp_path) -> None:
    from inference_engine.benchmarking.sqlite_ledger import SQLiteBenchmarkLedger

    ledger = SQLiteBenchmarkLedger(tmp_path / "ledger.sqlite3")
    baseline_trace = RequestTrace(
        request_id="1",
        provider="openai",
        model="baseline-model",
        latency_ms=200,
        prompt_tokens=10,
        completion_tokens=10,
        total_tokens=20,
        estimated_cost_usd=0.04,
        pricing_table_version="test",
        cache_hit=False,
        error_type=None,
        error_message=None,
        timestamp="2026-01-01T00:00:00+00:00",
    )
    candidate_trace = RequestTrace(
        request_id="2",
        provider="openai",
        model="candidate-model",
        latency_ms=100,
        prompt_tokens=10,
        completion_tokens=10,
        total_tokens=20,
        estimated_cost_usd=0.02,
        pricing_table_version="test",
        cache_hit=False,
        error_type=None,
        error_message=None,
        timestamp="2026-01-01T00:00:00+00:00",
    )
    baseline = summarize_traces(
        workload_path=tmp_path / "workload.jsonl",
        strategy="single_model",
        provider="openai",
        model="baseline-model",
        ledger_path=tmp_path / "baseline.jsonl",
        traces=[baseline_trace],
    )
    candidate = summarize_traces(
        workload_path=tmp_path / "workload.jsonl",
        strategy="rule_based",
        provider="openai",
        model="candidate-model",
        ledger_path=tmp_path / "candidate.jsonl",
        traces=[candidate_trace],
    )
    ledger.record_run(run_id="baseline", report=baseline, traces=[baseline_trace])
    ledger.record_run(run_id="candidate", report=candidate, traces=[candidate_trace])
    comparison_path = tmp_path / "comparison.json"

    exit_code = _compare(
        Namespace(
            sqlite_ledger_path=str(tmp_path / "ledger.sqlite3"),
            baseline_run_id="baseline",
            candidate_run_id="candidate",
            comparison_path=str(comparison_path),
        )
    )

    raw = json.loads(comparison_path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert raw["comparable"] is True
    assert raw["cost_delta_usd"] == pytest.approx(-0.02)
