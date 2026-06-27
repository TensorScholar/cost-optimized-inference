# LLM Inference Gateway Documentation

This documentation set describes the target project that should replace the current scaffold.

The intended project is a small but serious LLM inference gateway and benchmark lab:

- real provider calls, not echo responses;
- real latency and cost measurements, not invented dashboard values;
- policy-based routing, not generic "AI orchestration" language;
- reproducible benchmark reports suitable for GitHub and resume evidence.

## Documents

- [00 Strategy Brief](./00_STRATEGY_BRIEF.md): problem, target user, unique angle, non-goals, and success standard.
- [01 Target Architecture](./01_TARGET_ARCHITECTURE.md): components, request contract, routing, ledger, telemetry, and failure handling.
- [02 Implementation Roadmap](./02_IMPLEMENTATION_ROADMAP.md): phased tasks with acceptance criteria.
- [03 Benchmark And Eval Plan](./03_BENCHMARK_AND_EVAL_PLAN.md): workloads, baselines, cost/latency/quality measurement, and report format.
- [04 Codex Quality System](./04_CODEX_QUALITY_SYSTEM.md): how to use Codex app, AGENTS.md, skills, review loops, and hooks without turning the process into overhead.

## Principle

If the project cannot prove a cost or latency claim with a command and a generated report, the claim should not exist in the README.

