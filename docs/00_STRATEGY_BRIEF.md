# Strategy Brief: Honest SLO-Aware LLM Inference Gateway

## One-Line Positioning

Build a small, real LLM inference gateway that chooses the cheapest acceptable execution path for each request while preserving latency SLOs and measured answer quality.

## Why This Is Worth Building

Many engineering teams now have LLM usage in production but weak control over:

- model selection;
- token spend;
- retry cost;
- tail latency;
- prompt cacheability;
- async versus synchronous execution;
- quality loss when using cheaper models;
- observability across providers.

A strong portfolio project should solve this narrow problem end to end. It should not pretend to be a full ML platform. It should show senior judgment: measurable tradeoffs, careful failure behavior, small architecture, and honest evidence.

## Target User

The target user is a backend or platform engineer who owns an application that calls LLM providers and needs to answer:

- Which model should serve this request?
- Is this request urgent, or can it use a cheaper async path?
- Did routing save money without breaking quality?
- Which features, users, or endpoints drive cost?
- What happens when a provider times out, rate limits, or returns partial failure?

## Unique Angle

Most demo projects show routing logic without proof. This project should be different:

1. It has a gateway that executes real requests.
2. It has a ledger that stores actual usage, latency, and route decisions.
3. It has a benchmark runner that compares a baseline against optimized strategies.
4. It has an eval harness that detects quality degradation.
5. It has documentation that refuses unsupported claims.

## Market And Technology Anchors

The project should align with current LLM infrastructure trends:

- Provider batch APIs for cheaper offline work: OpenAI Batch API, https://platform.openai.com/docs/guides/batch
- Prompt caching and cache-aware prompt design: OpenAI prompt caching, https://platform.openai.com/docs/guides/prompt-caching
- Anthropic prompt caching for repeated context: https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching
- Prefix/KV cache reuse in local serving: vLLM automatic prefix caching, https://docs.vllm.ai/en/latest/features/automatic_prefix_caching/
- Standardized GenAI observability: OpenTelemetry semantic conventions, https://opentelemetry.io/docs/specs/semconv/gen-ai/
- Distributed inference systems focus on scheduling, routing, cache, and SLOs, not vague orchestration: NVIDIA Dynamo, https://developer.nvidia.com/dynamo

These are not features to copy blindly. They are signals about what serious companies care about: cost, latency, cache reuse, quality, routing, and operational evidence.

## Core Product Shape

The system exposes an OpenAI-like HTTP interface and adds policy fields:

```json
{
  "messages": [{"role": "user", "content": "Summarize this incident report"}],
  "policy": {
    "latency_slo_ms": 1500,
    "max_cost_usd": 0.02,
    "quality_tier": "standard",
    "allow_async": true,
    "allow_fallback": true,
    "cache_mode": "read_write"
  },
  "metadata": {
    "user_id": "u_123",
    "feature": "incident_summary",
    "experiment": "router_v1"
  }
}
```

The router decides:

- direct premium model;
- cheaper model;
- local model;
- async batch lane;
- cache-aware execution path;
- fallback after failure.

Every decision creates a ledger row.

## What The GitHub Repo Should Prove

The repo should make these claims only after evidence exists:

- "On workload X, strategy Y reduced measured provider cost by Z percent."
- "p95 latency stayed under SLO for synchronous requests."
- "Quality pass rate stayed above threshold on the eval suite."
- "Batch lane saved money for non-urgent requests with deadline greater than N."
- "Prompt cache advisor improved cache eligibility on repeated-prefix workloads."

## Non-Goals

The project should not initially build:

- Kubernetes deployment;
- multi-region control plane;
- generalized ML workflow platform;
- fake semantic response cache;
- full vendor marketplace;
- custom vector database;
- complete web dashboard;
- complex autoscaling;
- organization billing product.

Those are distractions until the measurable gateway works.

## What Makes It Resume-Strong

A strong resume bullet after completion should look like this:

> Built an SLO-aware LLM inference gateway that reduced measured inference cost by X percent on replayed workloads while preserving Y percent eval pass rate; implemented provider adapters, policy routing, async batch lane, prompt-cache-aware execution, cost ledger, OpenTelemetry traces, and reproducible benchmark reports.

That is stronger than broad claims about "production-grade architecture."

