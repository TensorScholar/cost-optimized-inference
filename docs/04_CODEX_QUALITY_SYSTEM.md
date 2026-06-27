# Codex Quality System

## Goal

Use Codex as a disciplined engineering loop, not as a code generator that inflates scope.

The project should use Codex surfaces in the smallest useful way:

- `AGENTS.md` for durable repo rules;
- repo skills for repeated review workflows;
- Plan mode for ambiguous architecture work;
- Goal mode for multi-step implementation with clear completion criteria;
- optional hooks only after manual review loops prove stable;
- Codex review for diffs and phase exits.

This follows the Codex manual guidance that good tasks include goal, context, constraints, and done criteria; reusable rules belong in `AGENTS.md`; repeated workflows can become skills; and hooks can enforce lifecycle checks when needed.

Official Codex references:

- Best practices: https://developers.openai.com/codex/learn/best-practices
- Prompting: https://developers.openai.com/codex/prompting
- Skills: https://developers.openai.com/codex/skills
- AGENTS.md: https://developers.openai.com/codex/guides/agents-md
- Hooks: https://developers.openai.com/codex/hooks

## Working Loop

Use this loop for every meaningful phase:

```text
Plan
  -> Implement smallest complete slice
  -> Test
  -> Benchmark or smoke evidence
  -> Codex review
  -> Human acceptance
  -> Update docs and AGENTS.md if a repeated rule emerged
```

## Prompt Pattern

For implementation prompts, use:

```text
Goal:
Implement [specific slice].

Context:
Use docs/[relevant_doc]. Follow AGENTS.md. Existing fake/stub behavior must be removed.

Constraints:
Keep the stack small. Do not add Kubernetes, TimescaleDB, dashboards, or extra providers.
Do not fake metrics or costs.

Done when:
- tests pass;
- route/usage/cost behavior is recorded in the ledger;
- docs match behavior;
- benchmark or smoke command proves the change.
```

## Recommended Repo Skills

Two repo-scoped skills are included:

- `inference-architecture-review`
- `benchmark-integrity-review`

Use them explicitly before major merges:

```text
$inference-architecture-review review the routing and provider adapter design in this diff.
```

```text
$benchmark-integrity-review review this benchmark report and tell me whether the claims are defensible.
```

## When To Create More Skills

Create a skill only after a review pattern repeats at least twice.

Good future skills:

- `provider-adapter-hardening`: timeout, retry, cancellation, usage accounting review.
- `cost-ledger-audit`: pricing, token accounting, and ledger consistency review.
- `eval-suite-review`: quality metrics and evaluator leakage review.
- `async-lane-review`: queue, worker, idempotency, and deadline behavior review.

Do not create skills for one-off tasks.

## Hook Strategy

Hooks can improve consistency, but they can also create noise. Add hooks only after the manual loop is stable.

Potential low-noise hooks:

- Stop hook that reminds the agent to report tests and benchmark evidence.
- PostToolUse hook that flags edits to README or status docs containing unsupported phrases like "production-ready" or fixed savings percentages.
- PreToolUse hook that warns before destructive git commands.

Do not add hooks that run full test suites after every command. That creates bottlenecks.

## Phase Exit Review

At the end of each phase, run a critical review against this checklist:

- Is the feature real or still a stub?
- Is there a test for the behavior?
- Is there a command that proves it?
- Did we add any infrastructure before proving need?
- Did latency get worse from avoidable serialization or blocking async code?
- Are cost numbers actual, calculated from provider usage, or clearly labeled estimates?
- Does documentation overclaim?
- Would this look credible to an ML platform or LLM infrastructure hiring manager?

## Codex App Usage

Use the Codex app for:

- planning and reviewing multi-file work;
- side-by-side diff review;
- browser-based local UI/API verification when needed;
- multiple threads only when they do not edit the same files;
- Goal mode for long implementation phases with measurable completion.

Avoid running parallel Codex threads on the same files. Use one implementation thread and separate read-only review threads if needed.

## Quality Bar

The best signal for this project is not code volume. It is evidence quality.

A small feature with:

- strict tests;
- real provider usage;
- a ledger row;
- a benchmark report;
- and an honest limitation section

is more impressive than a large fake platform.

