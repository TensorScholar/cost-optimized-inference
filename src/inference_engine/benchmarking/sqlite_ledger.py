from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from pathlib import Path

from ..infrastructure.telemetry.request_log import RequestTrace
from ..utils.time import utc_now
from .harness import BenchmarkReport

SCHEMA_VERSION = 1


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
                    timestamp TEXT NOT NULL,
                    PRIMARY KEY (run_id, request_id),
                    FOREIGN KEY (run_id) REFERENCES benchmark_runs(run_id) ON DELETE CASCADE
                )
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
                        trace.latency_ms,
                        trace.prompt_tokens,
                        trace.completion_tokens,
                        trace.total_tokens,
                        trace.estimated_cost_usd,
                        trace.pricing_table_version,
                        1 if trace.cache_hit else 0,
                        trace.error_type,
                        trace.error_message,
                        trace.timestamp,
                    )
                    for trace in traces
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
            )
            for row in rows
        ]

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection
