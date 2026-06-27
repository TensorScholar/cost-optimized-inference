# Implementation Roadmap

## Phase 0: Repo Repair And Truth Reset

Goal: make the repository honest and runnable.

Tasks:

- Restore or recreate missing package files.
- Restore `pyproject.toml` with strict tool configuration.
- Remove or rewrite fake production-ready status documents.
- Add `docs/` as the source of truth for the rebuild.
- Add minimal import smoke test.
- Add strict CI commands locally: ruff, mypy, pytest.

Acceptance criteria:

- `python -m pytest` collects tests successfully.
- `python -c "import inference_engine"` succeeds.
- No document claims unsupported production readiness.

## Phase 1: Core Request Model And Ledger

Goal: define the contract and store real events before optimizing anything.

Tasks:

- Implement typed request, policy, route decision, provider result, and usage models.
- Implement SQLite ledger with migrations or simple schema initializer.
- Add ledger repository methods for request, route, usage, and eval records.
- Add price table model with versioned source metadata.
- Add unit tests for cost calculation and ledger writes.

Acceptance criteria:

- A request can be recorded end to end without provider calls.
- Cost calculations use explicit price versions.
- Tests verify missing usage data does not produce fake cost.

## Phase 2: Real Provider Adapter

Goal: replace echo behavior with one real provider path.

Tasks:

- Implement OpenAI provider adapter first.
- Add timeout, retry, cancellation, and provider error classification.
- Extract prompt tokens, completion tokens, cached tokens when available, finish reason, and latency.
- Record usage in the ledger.
- Add an integration test that can run with a real API key and is skipped when the key is absent.
- Add a fake provider adapter for deterministic unit tests.

Acceptance criteria:

- Local smoke command makes a real provider request when configured.
- Ledger records real usage metadata.
- No provider path returns hardcoded cost or echo text.

## Phase 3: Policy Router V1

Goal: make routing useful but not overcomplicated.

Tasks:

- Create static model registry with provider, model, price, context, and quality tier.
- Implement policies:
  - `min_cost`
  - `min_latency`
  - `balanced`
  - `quality_required`
  - `deadline_aware`
- Add reason codes for every decision.
- Enforce `max_cost_usd`.
- Enforce `latency_slo_ms` using recent observed latency or default model profile.
- Add fallback chain with bounded retry budget.

Acceptance criteria:

- Router decisions are deterministic under controlled model profiles.
- Cost budget violation returns a structured error, not a surprise expensive call.
- Route decision is recorded before execution.

## Phase 4: Benchmark Harness

Goal: prove or disprove savings.

Tasks:

- Add workload format: JSONL with messages, metadata, expected behavior, and policy.
- Add baseline strategy: always use premium model.
- Add optimized strategy: policy router.
- Add benchmark runner CLI.
- Store each run in the ledger.
- Generate Markdown and JSON reports.

Acceptance criteria:

- One command runs baseline and optimized strategies on the same workload.
- Report includes total cost, p50/p95 latency, error rate, model distribution, and route reasons.
- Report refuses to compute savings if baseline data is missing.

## Phase 5: Eval-Aware Routing

Goal: stop cost optimization from silently destroying quality.

Tasks:

- Add small eval suites:
  - summarization faithfulness;
  - classification exactness;
  - extraction correctness;
  - simple coding or reasoning tasks.
- Add deterministic validators where possible.
- Add optional LLM-as-judge only where deterministic scoring is not enough.
- Store eval results by request and benchmark run.
- Add quality threshold to benchmark reports.

Acceptance criteria:

- Optimized strategy must report quality pass rate.
- Report separates cost savings from quality regressions.
- Routing to cheaper models is not considered successful unless quality threshold holds.

## Phase 6: Async Batch Lane

Goal: add a real cost lever for non-urgent work.

Tasks:

- Add async submission contract.
- Add local queue and worker first.
- Add status endpoint.
- Add deadline-aware routing into async lane.
- Add provider-native batch integration after local semantics are tested.
- Record queue time, completion time, final usage, and final status.

Acceptance criteria:

- Requests with loose deadlines can be executed asynchronously.
- Benchmark compares sync-only versus async-eligible workloads.
- Cost and latency accounting includes end-to-end async time.

## Phase 7: Prompt Cache Advisor

Goal: make cache behavior practical without unsafe semantic response caching.

Tasks:

- Detect stable prefix and volatile suffix in message sets.
- Identify cache-hostile prompt patterns:
  - timestamps in system prompt;
  - per-user data in prefix;
  - random IDs in repeated context;
  - changing instructions before static documents.
- Add cache eligibility score.
- Emit route reason `cache_prefix_eligible`.
- Add benchmark workload with repeated long prefix.

Acceptance criteria:

- Advisor produces actionable diagnostics.
- Benchmark reports cached token usage when provider returns it.
- Docs explicitly distinguish prompt/prefix caching from semantic response caching.

## Phase 8: Local vLLM Lane

Goal: demonstrate local serving knowledge without making it the whole project.

Tasks:

- Add optional vLLM adapter behind an extra dependency group.
- Keep local model startup outside normal test path.
- Avoid blocking async request loop.
- Add local-only benchmark profile.
- Compare provider versus local cost assumptions transparently.

Acceptance criteria:

- Default install does not require vLLM.
- Local adapter can be smoke-tested when model path is configured.
- Latency and token accounting are recorded separately from provider path.

## Phase 9: Codex Quality Automation

Goal: use Codex to improve quality consistently.

Tasks:

- Keep `AGENTS.md` concise and current.
- Use repo skills for architecture and benchmark review.
- Add optional hooks only after manual loops prove value.
- Add review checklist to pull request template.
- Run Codex review on major phases.

Acceptance criteria:

- Repeated review findings are converted into project guidance.
- Skills remain focused and short.
- Hooks do not block normal development with noisy false positives.

