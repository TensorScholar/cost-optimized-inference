from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path

from ..infrastructure.telemetry.request_log import RequestTrace, RouteTrace
from ..utils.time import utc_now
from .harness import BenchmarkReport

SCHEMA_VERSION = 2


@dataclass(frozen=True)
class ProviderUsageRecord:
    """Queryable provider usage row derived from one benchmark request trace."""

    request_id: str
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    pricing_table_version: str
    cache_hit: bool
    provider_attempt_count: int
    provider_retry_count: int
    error_type: str | None
    timestamp: str


@dataclass(frozen=True)
class ProviderUsageSummary:
    """Aggregated provider usage for a benchmark run."""

    run_id: str
    request_count: int
    success_count: int
    failure_count: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    provider_attempt_count: int
    provider_retry_count: int
    cost_by_model: dict[str, float]
    tokens_by_model: dict[str, int]


class SQLiteBenchmarkLedger:
    """Small local SQLite ledger for reproducible benchmark run comparisons."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS ledger_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS benchmark_runs (
                    run_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    workload_path TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    report_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS benchmark_traces (
                    run_id TEXT NOT NULL,
                    request_id TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    latency_ms INTEGER NOT NULL,
                    prompt_tokens INTEGER NOT NULL,
                    completion_tokens INTEGER NOT NULL,
                    total_tokens INTEGER NOT NULL,
                    estimated_cost_usd REAL NOT NULL,
                    pricing_table_version TEXT NOT NULL,
                    cache_hit INTEGER NOT NULL,
                    error_type TEXT,
                    error_message TEXT,
                    quality_passed INTEGER,
                    quality_score REAL,
                    quality_reason TEXT,
                    eval_type TEXT,
                    provider_attempt_count INTEGER NOT NULL DEFAULT 1,
                    provider_retry_count INTEGER NOT NULL DEFAULT 0,
                    timestamp TEXT NOT NULL,
                    PRIMARY KEY (run_id, request_id),
                    FOREIGN KEY (run_id) REFERENCES benchmark_runs(run_id) ON DELETE CASCADE
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS benchmark_provider_usage (
                    run_id TEXT NOT NULL,
                    request_id TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    prompt_tokens INTEGER NOT NULL,
                    completion_tokens INTEGER NOT NULL,
                    total_tokens INTEGER NOT NULL,
                    estimated_cost_usd REAL NOT NULL,
                    pricing_table_version TEXT NOT NULL,
                    cache_hit INTEGER NOT NULL,
                    provider_attempt_count INTEGER NOT NULL,
                    provider_retry_count INTEGER NOT NULL,
                    error_type TEXT,
                    timestamp TEXT NOT NULL,
                    PRIMARY KEY (run_id, request_id),
                    FOREIGN KEY (run_id) REFERENCES benchmark_runs(run_id) ON DELETE CASCADE
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS benchmark_routes (
                    run_id TEXT NOT NULL,
                    request_id TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    selected_model TEXT NOT NULL,
                    estimated_cost_usd REAL NOT NULL,
                    estimated_latency_ms INTEGER NOT NULL,
                    decision_reason TEXT NOT NULL,
                    considered_models_json TEXT NOT NULL,
                    fallback_models_json TEXT NOT NULL,
                    max_estimated_cost_usd REAL,
                    budget_violation INTEGER NOT NULL,
                    budget_violation_reason TEXT,
                    timestamp TEXT NOT NULL,
                    PRIMARY KEY (run_id, request_id),
                    FOREIGN KEY (run_id) REFERENCES benchmark_runs(run_id) ON DELETE CASCADE
                )
                """
            )
            _ensure_columns(
                connection,
                table_name="benchmark_traces",
                columns={
                    "quality_passed": "INTEGER",
                    "quality_score": "REAL",
                    "quality_reason": "TEXT",
                    "eval_type": "TEXT",
                    "provider_attempt_count": "INTEGER NOT NULL DEFAULT 1",
                    "provider_retry_count": "INTEGER NOT NULL DEFAULT 0",
                },
            )
            connection.execute(
                """
                INSERT OR IGNORE INTO benchmark_provider_usage (
                    run_id,
                    request_id,
                    provider,
                    model,
                    prompt_tokens,
                    completion_tokens,
                    total_tokens,
                    estimated_cost_usd,
                    pricing_table_version,
                    cache_hit,
                    provider_attempt_count,
                    provider_retry_count,
                    error_type,
                    timestamp
                )
                SELECT
                    run_id,
                    request_id,
                    provider,
                    model,
                    prompt_tokens,
                    completion_tokens,
                    total_tokens,
                    estimated_cost_usd,
                    pricing_table_version,
                    cache_hit,
                    provider_attempt_count,
                    provider_retry_count,
                    error_type,
                    timestamp
                FROM benchmark_traces
                """
            )
            connection.execute(
                """
                INSERT OR REPLACE INTO ledger_metadata (key, value)
                VALUES ('schema_version', ?)
                """,
                (str(SCHEMA_VERSION),),
            )

    def record_run(
        self,
        *,
        run_id: str,
        report: BenchmarkReport,
        traces: list[RequestTrace],
        route_traces: list[RouteTrace] | None = None,
    ) -> None:
        self.initialize()
        with self._connect() as connection:
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute(
                """
                INSERT OR REPLACE INTO benchmark_runs (
                    run_id, created_at, workload_path, strategy, provider, model, report_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    utc_now().isoformat(),
                    report.workload_path,
                    report.strategy,
                    report.provider,
                    report.model,
                    json.dumps(asdict(report), sort_keys=True),
                ),
            )
            connection.execute("DELETE FROM benchmark_traces WHERE run_id = ?", (run_id,))
            connection.execute("DELETE FROM benchmark_routes WHERE run_id = ?", (run_id,))
            connection.execute("DELETE FROM benchmark_provider_usage WHERE run_id = ?", (run_id,))
            connection.executemany(
                """
                INSERT INTO benchmark_traces (
                    run_id,
                    request_id,
                    provider,
                    model,
                    latency_ms,
                    prompt_tokens,
                    completion_tokens,
                    total_tokens,
                    estimated_cost_usd,
                    pricing_table_version,
                    cache_hit,
                    error_type,
                    error_message,
                    quality_passed,
                    quality_score,
                    quality_reason,
                    eval_type,
                    provider_attempt_count,
                    provider_retry_count,
                    timestamp
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        run_id,
                        trace.request_id,
                        trace.provider,
                        trace.model,
                        trace.latency_ms,
                        trace.prompt_tokens,
                        trace.completion_tokens,
                        trace.total_tokens,
                        trace.estimated_cost_usd,
                        trace.pricing_table_version,
                        1 if trace.cache_hit else 0,
                        trace.error_type,
                        trace.error_message,
                        _optional_bool_to_int(trace.quality_passed),
                        trace.quality_score,
                        trace.quality_reason,
                        trace.eval_type,
                        trace.provider_attempt_count,
                        trace.provider_retry_count,
                        trace.timestamp,
                    )
                    for trace in traces
                ],
            )
            connection.executemany(
                """
                INSERT INTO benchmark_provider_usage (
                    run_id,
                    request_id,
                    provider,
                    model,
                    prompt_tokens,
                    completion_tokens,
                    total_tokens,
                    estimated_cost_usd,
                    pricing_table_version,
                    cache_hit,
                    provider_attempt_count,
                    provider_retry_count,
                    error_type,
                    timestamp
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        run_id,
                        trace.request_id,
                        trace.provider,
                        trace.model,
                        trace.prompt_tokens,
                        trace.completion_tokens,
                        trace.total_tokens,
                        trace.estimated_cost_usd,
                        trace.pricing_table_version,
                        1 if trace.cache_hit else 0,
                        trace.provider_attempt_count,
                        trace.provider_retry_count,
                        trace.error_type,
                        trace.timestamp,
                    )
                    for trace in traces
                ],
            )
            connection.executemany(
                """
                INSERT INTO benchmark_routes (
                    run_id,
                    request_id,
                    strategy,
                    selected_model,
                    estimated_cost_usd,
                    estimated_latency_ms,
                    decision_reason,
                    considered_models_json,
                    fallback_models_json,
                    max_estimated_cost_usd,
                    budget_violation,
                    budget_violation_reason,
                    timestamp
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        run_id,
                        route.request_id,
                        route.strategy,
                        route.selected_model,
                        route.estimated_cost_usd,
                        route.estimated_latency_ms,
                        route.decision_reason,
                        json.dumps(route.considered_models, sort_keys=True),
                        json.dumps(route.fallback_models, sort_keys=True),
                        route.max_estimated_cost_usd,
                        1 if route.budget_violation else 0,
                        route.budget_violation_reason,
                        route.timestamp,
                    )
                    for route in (route_traces or [])
                ],
            )

    def get_report(self, run_id: str) -> BenchmarkReport:
        self.initialize()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT report_json FROM benchmark_runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"Unknown benchmark run_id: {run_id}")
        raw = json.loads(str(row["report_json"]))
        raw.setdefault("workload_sha256", None)
        raw.setdefault("route_count", 0)
        raw.setdefault("budget_violation_count", 0)
        raw.setdefault("model_distribution", {})
        raw.setdefault("route_reason_distribution", {})
        raw.setdefault("observed_latency_ms_by_model", {})
        raw.setdefault("provider_attempt_count", raw.get("request_count", 0))
        raw.setdefault("provider_retry_count", 0)
        raw.setdefault("quality_count", 0)
        raw.setdefault("quality_pass_count", 0)
        raw.setdefault("quality_pass_rate", None)
        raw.setdefault("quality_score_avg", None)
        return BenchmarkReport(**raw)

    def get_traces(self, run_id: str) -> list[RequestTrace]:
        self.initialize()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    request_id,
                    provider,
                    model,
                    latency_ms,
                    prompt_tokens,
                    completion_tokens,
                    total_tokens,
                    estimated_cost_usd,
                    pricing_table_version,
                    cache_hit,
                    error_type,
                    error_message,
                    quality_passed,
                    quality_score,
                    quality_reason,
                    eval_type,
                    provider_attempt_count,
                    provider_retry_count,
                    timestamp
                FROM benchmark_traces
                WHERE run_id = ?
                ORDER BY timestamp, request_id
                """,
                (run_id,),
            ).fetchall()
        return [
            RequestTrace(
                request_id=str(row["request_id"]),
                provider=str(row["provider"]),
                model=str(row["model"]),
                latency_ms=int(row["latency_ms"]),
                prompt_tokens=int(row["prompt_tokens"]),
                completion_tokens=int(row["completion_tokens"]),
                total_tokens=int(row["total_tokens"]),
                estimated_cost_usd=float(row["estimated_cost_usd"]),
                pricing_table_version=str(row["pricing_table_version"]),
                cache_hit=bool(row["cache_hit"]),
                error_type=row["error_type"],
                error_message=row["error_message"],
                timestamp=str(row["timestamp"]),
                quality_passed=_optional_int_to_bool(row["quality_passed"]),
                quality_score=row["quality_score"],
                quality_reason=row["quality_reason"],
                eval_type=row["eval_type"],
                provider_attempt_count=int(row["provider_attempt_count"]),
                provider_retry_count=int(row["provider_retry_count"]),
            )
            for row in rows
        ]

    def get_provider_usage(self, run_id: str) -> list[ProviderUsageRecord]:
        self.initialize()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    request_id,
                    provider,
                    model,
                    prompt_tokens,
                    completion_tokens,
                    total_tokens,
                    estimated_cost_usd,
                    pricing_table_version,
                    cache_hit,
                    provider_attempt_count,
                    provider_retry_count,
                    error_type,
                    timestamp
                FROM benchmark_provider_usage
                WHERE run_id = ?
                ORDER BY timestamp, request_id
                """,
                (run_id,),
            ).fetchall()
        return [
            ProviderUsageRecord(
                request_id=str(row["request_id"]),
                provider=str(row["provider"]),
                model=str(row["model"]),
                prompt_tokens=int(row["prompt_tokens"]),
                completion_tokens=int(row["completion_tokens"]),
                total_tokens=int(row["total_tokens"]),
                estimated_cost_usd=float(row["estimated_cost_usd"]),
                pricing_table_version=str(row["pricing_table_version"]),
                cache_hit=bool(row["cache_hit"]),
                provider_attempt_count=int(row["provider_attempt_count"]),
                provider_retry_count=int(row["provider_retry_count"]),
                error_type=row["error_type"],
                timestamp=str(row["timestamp"]),
            )
            for row in rows
        ]

    def get_provider_usage_summary(self, run_id: str) -> ProviderUsageSummary:
        usage = self.get_provider_usage(run_id)
        if not usage:
            self.get_report(run_id)
        cost_by_model: dict[str, float] = {}
        tokens_by_model: dict[str, int] = {}
        for record in usage:
            cost_by_model[record.model] = cost_by_model.get(record.model, 0.0) + (
                record.estimated_cost_usd
            )
            tokens_by_model[record.model] = tokens_by_model.get(record.model, 0) + (
                record.total_tokens
            )

        return ProviderUsageSummary(
            run_id=run_id,
            request_count=len(usage),
            success_count=sum(1 for record in usage if record.error_type is None),
            failure_count=sum(1 for record in usage if record.error_type is not None),
            prompt_tokens=sum(record.prompt_tokens for record in usage),
            completion_tokens=sum(record.completion_tokens for record in usage),
            total_tokens=sum(record.total_tokens for record in usage),
            estimated_cost_usd=sum(record.estimated_cost_usd for record in usage),
            provider_attempt_count=sum(record.provider_attempt_count for record in usage),
            provider_retry_count=sum(record.provider_retry_count for record in usage),
            cost_by_model=dict(sorted(cost_by_model.items())),
            tokens_by_model=dict(sorted(tokens_by_model.items())),
        )

    def get_routes(self, run_id: str) -> list[RouteTrace]:
        self.initialize()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    request_id,
                    strategy,
                    selected_model,
                    estimated_cost_usd,
                    estimated_latency_ms,
                    decision_reason,
                    considered_models_json,
                    fallback_models_json,
                    max_estimated_cost_usd,
                    budget_violation,
                    budget_violation_reason,
                    timestamp
                FROM benchmark_routes
                WHERE run_id = ?
                ORDER BY timestamp, request_id
                """,
                (run_id,),
            ).fetchall()
        return [
            RouteTrace(
                request_id=str(row["request_id"]),
                strategy=str(row["strategy"]),
                selected_model=str(row["selected_model"]),
                estimated_cost_usd=float(row["estimated_cost_usd"]),
                estimated_latency_ms=int(row["estimated_latency_ms"]),
                decision_reason=str(row["decision_reason"]),
                considered_models=[
                    str(item) for item in json.loads(str(row["considered_models_json"]))
                ],
                fallback_models=[str(item) for item in json.loads(str(row["fallback_models_json"]))],
                max_estimated_cost_usd=row["max_estimated_cost_usd"],
                budget_violation=bool(row["budget_violation"]),
                budget_violation_reason=row["budget_violation_reason"],
                timestamp=str(row["timestamp"]),
            )
            for row in rows
        ]

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection


def _optional_bool_to_int(value: bool | None) -> int | None:
    if value is None:
        return None
    return 1 if value else 0


def _optional_int_to_bool(value: object) -> bool | None:
    if value is None:
        return None
    return bool(value)


def _ensure_columns(
    connection: sqlite3.Connection,
    *,
    table_name: str,
    columns: dict[str, str],
) -> None:
    existing = {
        str(row["name"])
        for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    }
    for column_name, column_type in columns.items():
        if column_name not in existing:
            connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
