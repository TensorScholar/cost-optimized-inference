# AGENTS.md

## Project Direction

This repository should become an honest, reproducible LLM inference gateway and benchmark lab. The core value is not broad platform surface area. The core value is proving real cost, latency, and quality tradeoffs for LLM routing decisions.

## Non-Negotiable Engineering Rules

- Do not claim production readiness unless the code has real provider calls, strict CI, observable runtime behavior, and reproducible benchmark evidence.
- Do not add fake metrics, fake dashboards, echo responses, hardcoded savings, or placeholder integrations that present as complete.
- Prefer a narrow complete workflow over many incomplete platform components.
- Every optimization must have a baseline and a report with actual measured cost, latency, and quality impact.
- Keep the default stack small: FastAPI, provider SDKs, SQLite or DuckDB, pytest, ruff, mypy, and optional Redis only when the queue/cache path needs it.
- Avoid Kubernetes, TimescaleDB, service mesh, distributed schedulers, and multi-region abstractions until a local single-node benchmark proves the need.

## Done Means

- Relevant tests pass.
- Type and lint checks are strict, not ignored.
- Docs match implemented behavior.
- New public claims include evidence: command, fixture, workload, or benchmark report.
- Any new provider feature has timeout, retry, cancellation, error taxonomy, and cost accounting behavior.

## Review Expectations

- Review for correctness before style.
- Reject changes that improve appearances without measurable behavior.
- Look for hidden latency bottlenecks: blocking calls inside async code, unbounded concurrency, serialized batch paths, and unnecessary network calls.
- Look for hidden cost bugs: stale pricing, missing usage metadata, wrong token accounting, and retries that exceed budget.
- Look for quality regressions: cheaper model routing must be backed by eval results, not assumptions.

## Codex Workflow

- For difficult or ambiguous work, plan first and define acceptance criteria before coding.
- Use repo-scoped skills in `.agents/skills` for architecture and benchmark reviews.
- After implementation, run a self-review loop: tests, benchmark or smoke evidence, diff review, and documentation consistency check.

