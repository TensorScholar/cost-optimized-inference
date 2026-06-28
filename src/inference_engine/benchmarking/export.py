from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from ..infrastructure.telemetry.request_log import RequestTrace, RouteTrace
from .harness import BenchmarkReport


def export_run_json(
    *,
    run_id: str,
    report: BenchmarkReport,
    traces: list[RequestTrace],
    routes: list[RouteTrace],
    output_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "run_id": run_id,
        "report": asdict(report),
        "traces": [asdict(trace) for trace in traces],
        "routes": [asdict(route) for route in routes],
    }
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def export_run_markdown(
    *,
    run_id: str,
    report: BenchmarkReport,
    traces: list[RequestTrace],
    routes: list[RouteTrace],
    output_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# Benchmark Run `{run_id}`",
        "",
        "## Summary",
        "",
        f"- Workload: `{report.workload_path}`",
        f"- Workload SHA256: `{report.workload_sha256 or 'unavailable'}`",
        f"- Strategy: `{report.strategy}`",
        f"- Provider: `{report.provider}`",
        f"- Model profile: `{report.model}`",
        f"- Requests: {report.request_count}",
        f"- Successes: {report.success_count}",
        f"- Failures: {report.failure_count}",
        f"- Error rate: {_format_rate(report.error_rate)}",
        f"- Latency p50: {report.latency_p50_ms} ms",
        f"- Latency p95: {report.latency_p95_ms} ms",
        f"- Prompt tokens: {report.prompt_tokens}",
        f"- Completion tokens: {report.completion_tokens}",
        f"- Total tokens: {report.total_tokens}",
        f"- Estimated cost: ${report.estimated_cost_usd:.8f}",
        f"- Quality pass rate: {_format_optional_rate(report.quality_pass_rate)}",
        f"- Quality score average: {_format_optional_float(report.quality_score_avg)}",
        f"- Route decisions: {report.route_count}",
        f"- Budget violations: {report.budget_violation_count}",
        "",
        "## Model Distribution",
        "",
    ]
    if report.model_distribution:
        for model, count in report.model_distribution.items():
            lines.append(f"- `{model}`: {count}")
    else:
        lines.append("No successful model calls were recorded.")

    lines.extend(["", "## Observed Latency By Model", ""])
    if report.observed_latency_ms_by_model:
        lines.extend(["| Model | Count | p50 | p95 |", "| --- | ---: | ---: | ---: |"])
        for model, profile in report.observed_latency_ms_by_model.items():
            lines.append(
                f"| `{model}` | {profile['count']} | {profile['p50']} ms | {profile['p95']} ms |"
            )
    else:
        lines.append("No successful latency profiles were recorded.")

    lines.extend(["", "## Route Reason Distribution", ""])
    if report.route_reason_distribution:
        for reason, count in report.route_reason_distribution.items():
            lines.append(f"- {count} x {_escape_table(reason)}")
    else:
        lines.append("No route reasons were recorded.")

    lines.extend(
        [
            "",
            "## Route Decisions",
            "",
        ]
    )
    if routes:
        lines.extend(
            [
                "| Request | Strategy | Selected model | Estimated cost | Budget violation | Reason |",
                "| --- | --- | --- | ---: | --- | --- |",
            ]
        )
        for route in routes:
            lines.append(
                "| "
                f"`{route.request_id}` | "
                f"`{route.strategy}` | "
                f"`{route.selected_model}` | "
                f"${route.estimated_cost_usd:.8f} | "
                f"{route.budget_violation} | "
                f"{_escape_table(route.decision_reason)} |"
            )
    else:
        lines.append("No route decisions were recorded.")

    lines.extend(["", "## Request Outcomes", ""])
    if traces:
        lines.extend(
            [
                "| Request | Model | Latency | Tokens | Cost | Error | Quality |",
                "| --- | --- | ---: | ---: | ---: | --- | --- |",
            ]
        )
        for trace in traces:
            quality = (
                "n/a"
                if trace.quality_passed is None
                else f"{trace.quality_passed} ({trace.quality_score:.2f})"
            )
            lines.append(
                "| "
                f"`{trace.request_id}` | "
                f"`{trace.model}` | "
                f"{trace.latency_ms} ms | "
                f"{trace.total_tokens} | "
                f"${trace.estimated_cost_usd:.8f} | "
                f"{trace.error_type or 'none'} | "
                f"{quality} |"
            )
    else:
        lines.append("No request traces were recorded.")

    lines.extend(["", "## Limitations", ""])
    for limitation in report.limitations:
        lines.append(f"- {limitation}")
    lines.append("- This export is evidence for one run only; compare runs before discussing cost deltas.")
    lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")


def _format_rate(value: float) -> str:
    return f"{value * 100:.2f}%"


def _format_optional_rate(value: float | None) -> str:
    if value is None:
        return "n/a"
    return _format_rate(value)


def _format_optional_float(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.4f}"


def _escape_table(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")
