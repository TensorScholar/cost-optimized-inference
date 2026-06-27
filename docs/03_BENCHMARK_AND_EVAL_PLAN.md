# Benchmark And Eval Plan

## Purpose

The benchmark system is the credibility engine of the project. Without it, routing and cost optimization are just claims.

The benchmark must answer:

- How much did the optimized strategy cost?
- How much would the baseline have cost?
- What latency did users experience?
- Did quality degrade?
- Which routes created the savings?
- Which requests failed and why?

## Benchmark Modes

### Baseline

The baseline should be intentionally simple:

- always use one configured high-quality model;
- no async lane;
- no route optimization;
- no cache-specific prompt changes.

This is the comparison point.

### Optimized

The optimized strategy enables:

- policy routing;
- fallback;
- deadline-aware async routing;
- prompt cache advisor;
- cheaper model selection where quality allows it.

### Ablation Modes

Ablations show which optimization matters:

- router only;
- router plus fallback;
- router plus async;
- router plus prompt-cache-aware formatting;
- router plus eval gate.

## Workload Format

Use JSONL so workloads can be diffed and replayed.

```json
{
  "id": "w_001",
  "task_type": "summarization",
  "messages": [
    {"role": "system", "content": "You summarize incident reports."},
    {"role": "user", "content": "Incident text..."}
  ],
  "policy": {
    "latency_slo_ms": 2000,
    "max_cost_usd": 0.03,
    "quality_tier": "standard",
    "allow_async": false,
    "cache_mode": "read_write"
  },
  "expected": {
    "must_include": ["root cause", "impact", "next action"],
    "must_not_include": ["unsupported claim"]
  },
  "metadata": {
    "feature": "incident_summary"
  }
}
```

## Workload Suites

### Suite A: Short Interactive Requests

Purpose: test low latency and routing overhead.

Examples:

- rewrite;
- classification;
- short extraction;
- simple Q&A.

Success:

- routing overhead is small;
- p95 latency remains under SLO;
- cheap model routes do not fail exact validators.

### Suite B: Long Context Summarization

Purpose: test cost sensitivity and prompt cache potential.

Examples:

- incident report summaries;
- meeting notes;
- support transcript summaries.

Success:

- cost is measured from actual provider usage;
- quality scoring catches missing required facts;
- cache advisor identifies stable prefix opportunities.

### Suite C: Deadline-Based Offline Work

Purpose: test async batch lane.

Examples:

- bulk categorization;
- nightly report generation;
- dataset labeling;
- transcript post-processing.

Success:

- async lane is selected only when allowed;
- end-to-end completion time is measured;
- batch savings are reported separately from router savings.

### Suite D: Quality-Sensitive Tasks

Purpose: test that the router does not blindly optimize cost.

Examples:

- legal-ish policy extraction;
- medical-ish safety summary using synthetic data;
- financial risk classification using synthetic data;
- code reasoning tasks.

Success:

- premium or standard model is selected when cheaper model quality is insufficient;
- report shows quality threshold and pass rate.

## Metrics

### Cost

- total cost;
- cost per request;
- cost per 1k requests;
- cost by model;
- cost by feature;
- retry cost;
- fallback cost;
- cached token savings where provider exposes cached token usage.

### Latency

- p50;
- p90;
- p95;
- p99 if sample size supports it;
- provider latency;
- queue latency;
- routing overhead;
- eval overhead, reported separately from user path.

### Reliability

- success rate;
- timeout rate;
- rate-limit rate;
- fallback count;
- final failure count;
- budget-blocked count.

### Quality

- deterministic pass rate;
- LLM judge score when used;
- regression count versus baseline;
- quality-adjusted cost.

## Report Structure

Each benchmark should produce:

- `runs/<run_id>/report.md`
- `runs/<run_id>/summary.json`
- `runs/<run_id>/raw_events.jsonl`

Suggested report sections:

```text
Benchmark Summary
Configuration
Workload Description
Baseline Results
Optimized Results
Savings Analysis
Latency Analysis
Quality Analysis
Route Distribution
Failure Analysis
Threats To Validity
Reproduction Command
```

## Honesty Rules

- Do not show percentage savings without baseline.
- Do not compare different workloads.
- Do not hide failed requests.
- Do not include eval latency in user latency unless the eval ran on the user path.
- Do not use estimated token counts when provider usage exists.
- Do not call a benchmark "representative" unless workload source and assumptions are documented.

## Example Reproduction Command

```bash
llm-gateway bench run \
  --workload workloads/interactive_small.jsonl \
  --baseline always-premium \
  --candidate policy-router-v1 \
  --out runs/interactive-small-router-v1
```

## Minimum Good Result

The first impressive result does not need to be huge. A credible result is enough:

- 20 to 40 percent measured cost reduction;
- p95 latency within SLO;
- quality pass rate within 2 percent of baseline;
- clear explanation of which requests were routed differently.

That is much better than claiming 65 percent savings without proof.

