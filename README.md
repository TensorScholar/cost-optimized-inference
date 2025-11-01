## Cost-Optimized Inference Engine

Developers: Mohammad Atashi

### Summary

Intelligent LLM inference orchestration achieving up to 65% cost reduction with adaptive batching, multi-level caching, and cost-aware routing — while maintaining sub-100ms p95 latency for cached requests.

### Table of Contents
- Overview
- Key Features
- Architecture (High-Level)
- Quick Start
- Configuration
- API (Preview)
- Benchmarks (Summary)
- Roadmap
- Contributing & License

---

## Overview
The engine is a production-grade middleware that sits between your apps and LLM providers (OpenAI, Anthropic, self-hosted vLLM, etc.). It reduces operational costs by batching similar requests, caching semantically similar responses, and routing to the cheapest capable model.

What makes it different:
- Dynamic, SLA-aware batching (express/standard/batch lanes)
- Semantic and prefix caching (not just exact matches)
- Complexity-based model routing with fallbacks
- Real-time cost attribution and metrics

---

## Key Features
- Adaptive Dynamic Batching: Self-tunes batch size based on p95 latency targets.
- Multi-Level Caching: Exact, semantic (vector), and prefix/KV-cache reuse.
- Cost-Aware Routing: Selects cheapest model capable of fulfilling the request.
- Semantic Request Coalescing: Groups similar requests to maximize reuse.
- Observability: Prometheus metrics, tracing hooks, and structured logs.

---

## Architecture (High-Level)
```
Client Apps → FastAPI Gateway → Intelligent Batching → Multi-Level Cache → Cost-Aware Router → LLM Backends
                                                          │
                                                          └── Metrics/Cost Attribution/Logging
```
- Batching: Express (<50ms), Standard (<200ms), Batch (best-effort)
- Caches: Exact (Redis), Semantic (Vector index/FAISS), Prefix (KV reuse)
- Routing: Complexity estimator + cost/latency/health signals + fallbacks

---

## Quick Start

### Option 1: Docker Compose
```bash
# Clone
git clone https://github.com/TensorScholar/cost-optimized-inference.git
cd cost-optimized-inference

# Run (uses defaults; edit .env when needed)
docker-compose up -d

# Check health
curl http://localhost:8000/health
```

### Option 2: Local Dev
```bash
# Install (Poetry)
poetry install

# Run API
authentication is not required for local dev
make dev
# or
uvicorn inference_engine.adapters.api.app:app --reload --host 0.0.0.0 --port 8000

# Open docs
open http://localhost:8000/docs
```

---

## Configuration
Environment (commonly used):
```
REDIS_URL=redis://localhost:6379
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
ROUTING_STRATEGY=cost_optimal   # cost_optimal | latency_optimal | balanced
COST_WEIGHT=0.7                 # 0.0 (latency) → 1.0 (cost)
```
Defaults are managed via `src/inference_engine/config.py` (Pydantic settings).

---

## API (Preview)
- REST
  - POST /v1/inference: submit a single prompt
  - POST /v1/batch: submit multiple prompts
  - GET /health: liveness check
- WebSocket
  - /v1/stream: streaming output (stub)

Example request:
```json
POST /v1/inference
{
  "prompt": "Explain quantum computing simply",
  "max_tokens": 200,
  "temperature": 0.7,
  "priority": "standard",
  "use_cache": true
}
```

---

## Benchmarks (Summary)
- Throughput: up to 6–8x versus naive sequential
- Latency: p95 < 100–200ms with caching + batching
- Cost: up to ~65% reduction across common workloads

Note: Results vary by traffic pattern, cacheability, and backend models.

---

## Roadmap
- Advanced prompt normalization and cache policies
- Additional vector stores (Qdrant/Milvus) integrations
- Expanded routing strategies and model pools
- Richer dashboards and alerts (Grafana)
- SDKs for more languages

---

## Contributing & License
- Issues/PRs are welcome.
- License: MIT (see LICENSE).
