# Target Architecture

## Architectural Rule

The architecture should be boring at the edges and sharp in the middle.

Boring edges:

- FastAPI HTTP service.
- SQLite or DuckDB for local ledger.
- Provider SDK adapters.
- pytest, ruff, mypy.
- Markdown/HTML benchmark reports.

Sharp middle:

- policy-aware routing;
- cost ledger;
- quality-aware benchmark loop;
- failure and budget handling;
- cache-aware prompt execution.

## Logical Flow

```text
Client
  -> API Gateway
  -> Request Normalizer
  -> Policy Router
  -> Execution Lane
       -> Sync Provider Adapter
       -> Async Batch Adapter
       -> Local vLLM Adapter
  -> Usage Ledger
  -> Telemetry Exporter
  -> Benchmark/Eval Reporter
```

## Core Modules

### 1. API Gateway

Responsibilities:

- validate request schema;
- attach request ID;
- enforce request size limits;
- map client policy fields into internal policy model;
- return structured route metadata when requested.

Non-responsibilities:

- provider-specific logic;
- cost calculations;
- benchmark logic.

### 2. Request Normalizer

Responsibilities:

- normalize messages into a canonical request object;
- estimate input tokens before routing;
- compute cache eligibility hints;
- separate stable prefix from volatile suffix when possible;
- redact sensitive metadata before logs.

Important rule: token estimates are only estimates. Final cost must use provider usage metadata when available.

### 3. Policy Router

Inputs:

- estimated tokens;
- policy fields;
- model registry;
- current health state;
- recent latency samples;
- price table version;
- eval quality profile;
- cache eligibility;
- deadline or latency SLO.

Outputs:

- selected model;
- selected lane;
- fallback chain;
- max retry budget;
- predicted cost;
- predicted latency;
- reason codes.

Example reason codes:

- `within_cost_budget`
- `premium_required_by_quality_tier`
- `async_allowed_deadline_sufficient`
- `cache_prefix_eligible`
- `fallback_due_to_rate_limit`
- `blocked_cost_budget_exceeded`

### 4. Execution Lanes

#### Sync Lane

Used when the request has a near-term latency SLO.

Required behavior:

- timeout per provider call;
- cancellation propagation;
- retry only if idempotent and within budget;
- no unbounded concurrency;
- classify provider errors.

#### Async Batch Lane

Used when `allow_async=true` and a deadline is loose enough.

Required behavior:

- persist batch item before external call;
- expose status endpoint;
- record final usage and latency from submission to completion;
- support replayable benchmark mode.

Initial implementation can use a local queue and a worker. Provider-native batch integration can be added after the local contract is proven.

#### Local vLLM Lane

Optional after the provider path is solid.

Required behavior:

- do not block the FastAPI event loop with synchronous generation calls;
- isolate model startup from request path;
- expose health and capacity;
- measure queue time separately from generation time;
- report prompt and completion token counts.

### 5. Provider Adapters

Each adapter must implement:

```python
class ProviderAdapter(Protocol):
    async def complete(self, request: NormalizedRequest, budget: ExecutionBudget) -> ProviderResult: ...
    async def stream(self, request: NormalizedRequest, budget: ExecutionBudget) -> AsyncIterator[ProviderChunk]: ...
    async def health(self) -> ProviderHealth: ...
```

Required adapter fields:

- provider name;
- model name;
- timeout behavior;
- retryable error types;
- rate-limit metadata extraction;
- usage metadata extraction;
- finish reason mapping.

No adapter is complete until it records real usage and failure behavior.

### 6. Cost Ledger

The ledger is the source of truth. It should be append-friendly and easy to query.

Suggested tables:

```text
requests
  id
  created_at
  feature
  user_hash
  policy_json
  input_token_estimate
  status

route_decisions
  id
  request_id
  selected_provider
  selected_model
  selected_lane
  fallback_chain_json
  estimated_cost_usd
  estimated_latency_ms
  reason_codes_json
  price_version

provider_usage
  id
  request_id
  provider
  model
  prompt_tokens
  completion_tokens
  cached_tokens
  provider_reported_cost_usd
  calculated_cost_usd
  latency_ms
  queue_ms
  error_type
  finish_reason

eval_results
  id
  request_id
  eval_suite
  score
  pass
  judge_model
  notes

price_versions
  id
  provider
  model
  input_per_1m_tokens
  output_per_1m_tokens
  cached_input_per_1m_tokens
  effective_from
  source_url
```

Use SQLite first. Move to DuckDB if local analytics become painful. Do not add TimescaleDB until the project has multi-run benchmark history that needs it.

### 7. Observability

Emit structured logs and traces for:

- request received;
- route decision;
- provider call start/stop;
- retry/fallback;
- cache eligibility;
- cost recorded;
- eval result.

Use OpenTelemetry GenAI semantic conventions where practical. The initial goal is trace usefulness, not perfect vendor-dashboard polish.

### 8. Failure Model

Classify failures into:

- validation error;
- cost budget exceeded;
- latency budget impossible;
- provider timeout;
- provider rate limit;
- provider overload;
- provider auth/config error;
- unsafe retry;
- output policy failure;
- eval quality failure.

Each failure should have:

- user-safe error response;
- internal error type;
- retry/fallback policy;
- ledger record.

### 9. Minimal Runtime Deployment

Initial runtime:

```text
api process
sqlite/duckdb file
optional local worker process
optional redis for queue only after local queue limits are proven
```

This is enough for a serious GitHub project and avoids infrastructure theater.

