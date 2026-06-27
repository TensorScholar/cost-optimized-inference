---
name: inference-architecture-review
description: Review LLM inference gateway architecture changes for real behavior, latency risks, cost accounting bugs, provider failure handling, and over-engineering. Use before merging routing, provider adapter, queue, cache, or observability changes.
---

# Inference Architecture Review

Act as a senior LLM infrastructure reviewer. Prioritize correctness, latency, reliability, and honest cost accounting over style.

## Review Inputs

- Relevant code diff.
- Related docs under `docs/`.
- Test output or explicit statement that tests were not run.
- Benchmark or smoke evidence if the change affects runtime behavior.

## Review Checklist

1. Reality check
   - Does the change execute real behavior, or does it add a placeholder?
   - Are mock paths clearly test-only?
   - Are docs aligned with implemented behavior?

2. Latency
   - Any blocking work inside async paths?
   - Any accidental sequential loops in batch or concurrent paths?
   - Any unbounded concurrency?
   - Is queue time separated from provider time?

3. Provider resilience
   - Explicit timeout?
   - Retry policy bounded by cost and latency budget?
   - Cancellation propagation?
   - Error taxonomy for timeout, rate limit, auth/config, overload, invalid request?
   - Fallback behavior recorded and testable?

4. Cost
   - Uses provider usage metadata when available?
   - Uses versioned pricing when calculating cost?
   - Records retry and fallback cost?
   - Avoids hardcoded savings claims?

5. Scope
   - Does this add infrastructure before proving need?
   - Could a simpler local mechanism solve the current phase?

## Output Format

Start with findings ordered by severity. Include file and line references when possible.

Then include:

- residual risk;
- missing tests or benchmark evidence;
- recommended next change.

