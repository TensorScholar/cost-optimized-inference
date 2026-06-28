# Honest LLM Inference Gateway

An SLO-aware LLM inference gateway and benchmark lab for proving real cost, latency, and quality tradeoffs in model routing.

This project is intentionally narrow: it is not a fake "production platform" and it does not claim savings without evidence. The goal is to build the kind of infrastructure artifact that matters in real AI platform work: route requests by policy, record actual usage, compare against a baseline, and report whether the optimization was worth it.

## Why This Exists

LLM systems often start with one model and one provider call. That is simple, but it becomes expensive and hard to reason about once traffic grows. Teams need to answer practical questions:

- Which model should handle this request?
- Is the request latency-sensitive, or can it use a cheaper async path?
- Did routing save money without degrading quality?
- Which feature, user, or workload is driving spend?
- Are cost and latency claims backed by reproducible measurements?

This repository is being rebuilt around those questions.

## Current Status

**Phase 0 baseline repair is complete. Phase 1 implementation has started.**

The repository now has:

- an importable Python package baseline;
- strict local gates for lint, type checking, and tests;
- early domain primitives for batching, caching, routing, and cost calculation;
- an OpenAI-compatible provider adapter with timeout configuration, bounded retries, cancellation propagation, normalized provider errors, usage extraction, and real cost accounting;
- a versioned pricing table for supported model cost estimates;
- an append-only JSONL request ledger for local smoke and benchmark runs;
- a local SQLite benchmark ledger that stores run summaries and request traces by `run_id`;
- a small `inference-smoke` CLI for one real provider call;
- a benchmark harness with a replayable JSONL workload, JSON report output, and baseline-vs-candidate comparison from stored runs;
- deterministic quality validators for workload-declared checks: JSON keys, exact match, and required substrings;
- deterministic `single_model` and `rule_based` baseline routing modes;
- route decision traces with selected model, considered models, fallback models, reason, estimated latency, and estimated cost;
- pre-provider estimated cost budget enforcement for benchmark runs;
- architecture and benchmark planning docs under [docs/](./docs/README.md);
- repo-level Codex guidance and review skills for keeping future work honest.

Not implemented yet:

- provider usage storage in SQLite or DuckDB;
- policy router with observed latency profiles and richer budget policies;
- published measured savings reports;
- broad semantic quality evaluation beyond deterministic validators;
- async batch lane;
- prompt cache advisor.

## What Makes It Different

The project is designed around evidence, not dashboard theater.

Every future optimization should produce:

- a baseline comparison;
- actual provider usage or clearly labeled estimates;
- p50/p95 latency;
- quality or correctness results;
- route decision records;
- a reproducible command.

If a cost reduction cannot be reproduced from a benchmark report, it does not belong in the README.

## Target Architecture

```text
Client
  -> FastAPI Gateway
  -> Request Normalizer
  -> Policy Router
  -> Execution Lane
       -> Sync Provider Adapter
       -> Async Batch Adapter
       -> Local vLLM Adapter
  -> Usage Ledger
  -> Benchmark / Eval Reporter
```

Initial implementation stays small: FastAPI, typed domain models, SQLite or DuckDB for the ledger, pytest, ruff, mypy, and provider adapters only when they record real usage.

## Development

Create the local environment:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
```

Run the verified gates:

```bash
make check
```

Equivalent explicit commands:

```bash
.venv/bin/python -m ruff check src tests
.venv/bin/python -m mypy src
.venv/bin/python -m pytest
```

Current baseline:

```text
ruff:  all checks passed
mypy:  no issues found in 81 source files
pytest: 63 passed
```

Run one real provider smoke call when `OPENAI_API_KEY` is set:

```bash
.venv/bin/python -m inference_engine.cli \
  --provider openai \
  --model gpt-4o-mini \
  --prompt "Return JSON only with keys status and reason."
```

Run the v0 benchmark harness:

```bash
.venv/bin/python scripts/run_benchmark.py \
  run \
  --workload benchmarks/workloads/smoke.jsonl \
  --strategy single_model \
  --model gpt-4o-mini \
  --max-estimated-cost-usd 0.01 \
  --run-id baseline-gpt-4o-mini
```

Run a candidate strategy on the same workload:

```bash
.venv/bin/python scripts/run_benchmark.py \
  run \
  --workload benchmarks/workloads/smoke.jsonl \
  --strategy rule_based \
  --run-id candidate-rule-based
```

Compare stored runs:

```bash
.venv/bin/python scripts/run_benchmark.py \
  compare \
  --baseline-run-id baseline-gpt-4o-mini \
  --candidate-run-id candidate-rule-based
```

## Roadmap

1. **Phase 1: Real provider path and local ledger**
   OpenAI-compatible execution, normalized errors, cost accounting, request tracing, and smoke CLI.

2. **Phase 2: Evidence reports**
   Generate committed benchmark artifacts from real API-key runs, including quality pass rate, cost, latency, and limitations.

3. **Phase 3: Policy router**
   Route by cost, latency SLO, quality tier, deadline, and fallback constraints.

4. **Phase 4: Eval-aware routing**
   Prevent cheaper routing from silently degrading answer quality.

5. **Phase 5: Async batch lane and prompt-cache advisor**
   Add real cost levers for non-urgent and repeated-prefix workloads.

See [Implementation Roadmap](./docs/02_IMPLEMENTATION_ROADMAP.md) for acceptance criteria.

## Documentation

- [Strategy Brief](./docs/00_STRATEGY_BRIEF.md)
- [Target Architecture](./docs/01_TARGET_ARCHITECTURE.md)
- [Implementation Roadmap](./docs/02_IMPLEMENTATION_ROADMAP.md)
- [Benchmark And Eval Plan](./docs/03_BENCHMARK_AND_EVAL_PLAN.md)
- [Codex Quality System](./docs/04_CODEX_QUALITY_SYSTEM.md)

## Principle

Small, real, measurable infrastructure beats a large scaffold with fake production claims.
