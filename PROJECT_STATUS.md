# Project Status

## Current State

This repository has completed **Phase 0: repo repair and truth reset** and now has the first concrete Phase 1 implementation slices.

The previous status language claimed production readiness and complete infrastructure. That is no longer treated as accurate. The project is being narrowed into an honest SLO-aware LLM inference gateway and benchmark lab.

## What Is True Now

- The strategy, architecture, roadmap, benchmark plan, and Codex quality workflow are documented under [docs/](./docs/README.md).
- Early domain primitives for batching, caching, routing, and cost calculation are importable.
- OpenAI-compatible provider execution is implemented with bounded retries, timeout configuration, cancellation propagation, normalized provider errors, and usage extraction.
- Cost accounting uses a versioned model pricing table and fails on unknown pricing instead of inventing a value.
- Request traces can be appended to a local JSONL ledger.
- `inference-smoke` can make one real provider call when `OPENAI_API_KEY` is set.
- `scripts/run_benchmark.py run` can replay `benchmarks/workloads/smoke.jsonl`, write a JSON report, and store run data in a local SQLite ledger.
- `scripts/run_benchmark.py compare` can compare two stored run summaries from the SQLite ledger.
- Workload rows can declare deterministic quality validators: JSON keys, exact match, and required substrings.
- Benchmark reports include quality count, pass count, pass rate, and average deterministic score.
- Comparisons are not marked comparable when candidate quality pass rate is below baseline.
- Deterministic `single_model` and `rule_based` baseline routing modes are implemented for future comparisons.
- Local `.venv` gates pass for tests, lint, typecheck, and import smoke.

## What Is Not Implemented Yet

- Policy router with budget enforcement and observed latency profiles.
- Published baseline-vs-candidate savings reports with real run artifacts.
- Semantic quality evaluation beyond simple deterministic validators.
- Eval-aware routing.
- Async batch lane.
- Prompt cache advisor.
- Local vLLM lane.
- Production deployment.

## Phase 0 Acceptance Criteria

- `python -c "import inference_engine"` succeeds. Done.
- `.venv/bin/python -m pytest` collects and runs the current tests. Done.
- `.venv/bin/python -m ruff check src tests` passes. Done.
- `.venv/bin/python -m mypy src` passes. Done.
- Public documentation no longer claims unsupported production readiness. Done.
- Tooling configuration exists for strict lint/type/test checks. Done.

## Current Verification

- `.venv/bin/python -m ruff check src tests`: passed.
- `.venv/bin/python -m mypy src`: passed, 80 source files.
- `.venv/bin/python -m pytest`: passed, 58 tests.
- `.venv/bin/python scripts/run_benchmark.py ...` without `OPENAI_API_KEY`: exits before network access with a clear configuration error.

## Source Of Truth

Use these documents for future work:

- [Strategy Brief](./docs/00_STRATEGY_BRIEF.md)
- [Target Architecture](./docs/01_TARGET_ARCHITECTURE.md)
- [Implementation Roadmap](./docs/02_IMPLEMENTATION_ROADMAP.md)
- [Benchmark And Eval Plan](./docs/03_BENCHMARK_AND_EVAL_PLAN.md)
- [Codex Quality System](./docs/04_CODEX_QUALITY_SYSTEM.md)
