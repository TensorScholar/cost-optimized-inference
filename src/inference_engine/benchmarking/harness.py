from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path

from ..infrastructure.telemetry.request_log import RequestTrace


@dataclass(frozen=True)
class WorkloadItem:
    """One prompt in a replayable benchmark workload."""

    id: str
    prompt: str
    tags: dict[str, str]


@dataclass(frozen=True)
class BenchmarkReport:
    """Aggregate report generated from raw request trace records."""

    workload_path: str
    workload_sha256: str | None
    strategy: str
    provider: str
    model: str
    request_count: int
    success_count: int
    failure_count: int
    error_rate: float
    latency_p50_ms: int
    latency_p95_ms: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    ledger_path: str
    limitations: list[str]


@dataclass(frozen=True)
class BenchmarkComparison:
    """Comparison between one baseline run and one candidate run."""

    baseline_run_id: str
    candidate_run_id: str
    workload_path: str
    baseline_strategy: str
    candidate_strategy: str
    baseline_cost_usd: float
    candidate_cost_usd: float
    cost_delta_usd: float
    cost_delta_percent: float | None
    baseline_latency_p95_ms: int
    candidate_latency_p95_ms: int
    latency_p95_delta_ms: int
    baseline_error_rate: float
    candidate_error_rate: float
    comparable: bool
    limitations: list[str]


def load_workload(path: Path) -> list[WorkloadItem]:
    items: list[WorkloadItem] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            raw = json.loads(line)
            item_id = raw.get("id")
            prompt = raw.get("prompt")
            tags = raw.get("tags", {})
            if not isinstance(item_id, str) or not item_id:
                raise ValueError(f"{path}:{line_number} missing string id")
            if not isinstance(prompt, str) or not prompt:
                raise ValueError(f"{path}:{line_number} missing string prompt")
            if not isinstance(tags, dict) or not all(
                isinstance(key, str) and isinstance(value, str) for key, value in tags.items()
            ):
                raise ValueError(f"{path}:{line_number} tags must be an object of strings")
            items.append(WorkloadItem(id=item_id, prompt=prompt, tags=tags))
    if not items:
        raise ValueError(f"{path} did not contain any workload items")
    return items


def summarize_traces(
    *,
    workload_path: Path,
    strategy: str,
    provider: str,
    model: str,
    ledger_path: Path,
    traces: list[RequestTrace],
) -> BenchmarkReport:
    latencies = sorted(trace.latency_ms for trace in traces)
    success_traces = [trace for trace in traces if trace.error_type is None]
    request_count = len(traces)
    failure_count = request_count - len(success_traces)
    return BenchmarkReport(
        workload_path=str(workload_path),
        workload_sha256=_file_sha256(workload_path),
        strategy=strategy,
        provider=provider,
        model=model,
        request_count=request_count,
        success_count=len(success_traces),
        failure_count=failure_count,
        error_rate=failure_count / request_count if request_count else 0.0,
        latency_p50_ms=_percentile(latencies, 50),
        latency_p95_ms=_percentile(latencies, 95),
        prompt_tokens=sum(trace.prompt_tokens for trace in success_traces),
        completion_tokens=sum(trace.completion_tokens for trace in success_traces),
        total_tokens=sum(trace.total_tokens for trace in success_traces),
        estimated_cost_usd=sum(trace.estimated_cost_usd for trace in success_traces),
        ledger_path=str(ledger_path),
        limitations=[
            "Cost is calculated from provider usage metadata and the repository pricing table.",
            "This v0 report does not include quality scoring or savings claims.",
        ],
    )


def write_report(report: BenchmarkReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(asdict(report), handle, indent=2, sort_keys=True)
        handle.write("\n")


def compare_reports(
    *,
    baseline_run_id: str,
    baseline: BenchmarkReport,
    candidate_run_id: str,
    candidate: BenchmarkReport,
) -> BenchmarkComparison:
    same_workload_path = baseline.workload_path == candidate.workload_path
    same_workload_hash = (
        baseline.workload_sha256 == candidate.workload_sha256
        if baseline.workload_sha256 is not None and candidate.workload_sha256 is not None
        else True
    )
    same_request_count = baseline.request_count == candidate.request_count
    same_workload = same_workload_path and same_workload_hash and same_request_count
    comparable = same_workload and baseline.provider == candidate.provider
    cost_delta = candidate.estimated_cost_usd - baseline.estimated_cost_usd
    cost_delta_percent = (
        (cost_delta / baseline.estimated_cost_usd) * 100
        if baseline.estimated_cost_usd > 0
        else None
    )
    limitations = [
        "Comparison uses stored run summaries from the local SQLite ledger.",
        "No quality score is included yet; do not claim savings until quality evaluation exists.",
    ]
    if not same_workload_path:
        limitations.append("Runs used different workload paths and are not comparable.")
    if not same_workload_hash:
        limitations.append("Runs used different workload hashes and are not comparable.")
    if not same_request_count:
        limitations.append("Runs used different request counts and are not comparable.")
    if baseline.provider != candidate.provider:
        limitations.append("Runs used different providers and are not comparable.")

    return BenchmarkComparison(
        baseline_run_id=baseline_run_id,
        candidate_run_id=candidate_run_id,
        workload_path=baseline.workload_path,
        baseline_strategy=baseline.strategy,
        candidate_strategy=candidate.strategy,
        baseline_cost_usd=baseline.estimated_cost_usd,
        candidate_cost_usd=candidate.estimated_cost_usd,
        cost_delta_usd=cost_delta,
        cost_delta_percent=cost_delta_percent,
        baseline_latency_p95_ms=baseline.latency_p95_ms,
        candidate_latency_p95_ms=candidate.latency_p95_ms,
        latency_p95_delta_ms=candidate.latency_p95_ms - baseline.latency_p95_ms,
        baseline_error_rate=baseline.error_rate,
        candidate_error_rate=candidate.error_rate,
        comparable=comparable,
        limitations=limitations,
    )


def write_comparison(comparison: BenchmarkComparison, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(asdict(comparison), handle, indent=2, sort_keys=True)
        handle.write("\n")


def _percentile(values: list[int], percentile: int) -> int:
    if not values:
        return 0
    if len(values) == 1:
        return values[0]
    index = round((percentile / 100) * (len(values) - 1))
    return values[index]


def _file_sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
