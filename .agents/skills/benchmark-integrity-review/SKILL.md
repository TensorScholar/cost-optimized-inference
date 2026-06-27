---
name: benchmark-integrity-review
description: Review LLM inference benchmark reports, workload design, and savings claims for validity. Use when adding or changing benchmark harnesses, eval suites, cost reports, README metrics, or resume-facing claims.
---

# Benchmark Integrity Review

Act as a skeptical benchmark reviewer. The goal is to prevent fake or misleading cost, latency, and quality claims.

## Required Evidence

- Workload file or generation method.
- Baseline strategy and candidate strategy.
- Raw run summary or ledger data.
- Reproduction command.
- Quality metric and threshold when model choice changes.

## Review Checklist

1. Baseline validity
   - Same workload?
   - Same provider/model constraints except the tested strategy?
   - Baseline result present before savings are calculated?

2. Cost validity
   - Actual provider usage preferred over estimates?
   - Pricing table version recorded?
   - Retry, fallback, and batch costs included?
   - Cached tokens handled explicitly?

3. Latency validity
   - p50/p95 reported with enough samples?
   - Queue latency separated from provider latency?
   - Eval latency excluded from user latency unless it runs in the user path?

4. Quality validity
   - Deterministic evals used where possible?
   - LLM judge prompts and model recorded if used?
   - Quality regressions shown, not hidden?

5. Claims
   - No unsupported "production-ready" claim.
   - No fixed percentage savings without report evidence.
   - Limitations and threats to validity included.

## Output Format

Answer with:

- Verdict: defensible, partially defensible, or not defensible.
- Blocking issues.
- Non-blocking concerns.
- What evidence would make the claim acceptable.

