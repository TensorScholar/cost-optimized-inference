# Project Status

## Current State

This repository has completed the first baseline pass of **Phase 0: repo repair and truth reset**.

The previous status language claimed production readiness and complete infrastructure. That is no longer treated as accurate. The project is being narrowed into an honest SLO-aware LLM inference gateway and benchmark lab.

## What Is True Now

- The strategy, architecture, roadmap, benchmark plan, and Codex quality workflow are documented under [docs/](./docs/README.md).
- A minimal Python package structure is being restored.
- Early domain primitives for batching, caching, routing, and cost calculation are importable.
- Existing tests are being used as a repair gate for the Phase 0 baseline.
- Local `.venv` gates pass for tests, lint, typecheck, and import smoke.

## What Is Not Implemented Yet

- Real OpenAI or Anthropic provider execution.
- Provider usage ledger.
- Versioned pricing table.
- Policy router with budget enforcement.
- Reproducible benchmark runner.
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

## Source Of Truth

Use these documents for future work:

- [Strategy Brief](./docs/00_STRATEGY_BRIEF.md)
- [Target Architecture](./docs/01_TARGET_ARCHITECTURE.md)
- [Implementation Roadmap](./docs/02_IMPLEMENTATION_ROADMAP.md)
- [Benchmark And Eval Plan](./docs/03_BENCHMARK_AND_EVAL_PLAN.md)
- [Codex Quality System](./docs/04_CODEX_QUALITY_SYSTEM.md)
