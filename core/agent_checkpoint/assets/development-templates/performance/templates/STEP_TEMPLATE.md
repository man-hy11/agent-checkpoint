# Performance Optimization Step <ID> — <TITLE>

## Target
- Step: <ID>
- Scope: **Only this Step**

## Goal

<Precise performance goal — one or two sentences, not a restated title.
Name the specific metric and target (e.g. "reduce p95 latency of endpoint X
from 800ms to under 300ms under workload Y").>

## Preconditions

<Which earlier Step(s)/Gate(s) must already be verified complete. A baseline
Step (see `BENCHMARK_BASELINE.md`) must exist and be measured before any
optimization Step may claim improvement.>

## Required Reading / Existing System Inspection

Before implementing, read:
- repository agent instructions (`AGENTS.md` / `CLAUDE.md`);
- this work package (`WORK.md`);
- `CURRENT.md`;
- `BENCHMARK_BASELINE.md` — Performance Question, Metric, Workload,
  Environment, Baseline table, Measurement Procedure, Correctness Guard, and
  Anti-Cheating Checks relevant to this Step;
- relevant source-of-truth architecture/data-contract docs;
- the current implementation of the code path this Step targets (profiling
  output, existing benchmarks/load-test scripts, prior optimization
  attempts) — inspect actual measured behavior, not an assumed hotspot;
- existing benchmarking/profiling tooling already used in this repository —
  extend it rather than introducing a second measurement mechanism;
- affected tests/contracts, especially correctness tests for the code path
  being optimized;
- resource/infrastructure constraints (instance size, DB tier, concurrency
  limits) that bound what "environment" means for this Step's measurements.

## Scope

### In Scope
- ...

### Out of Scope
- ...

## Implement

<High-level shape of the optimization this Step makes — the "what," before
the Task-by-Task "how" below. State the specific metric/workload/threshold
this Step targets, taken from `BENCHMARK_BASELINE.md` or refining it.>

## Granular Execution Tasks

> Execute each Task in order and collect evidence before proceeding. See
> `shared/TASK_DECOMPOSITION_STANDARD.md` for the required structure of each
> Task below. For performance work, every Task's Implementation Contract
> must name the specific metric/workload/threshold it targets, and every
> Task's evidence must include actual before/after numbers.

### Task 1 — <imperative, specific action>

#### Objective
...

#### Inspect Before Editing
- exact files/modules/hot paths this Task is expected to touch or extend;
- current measured value of the metric this Task targets, from
  `BENCHMARK_BASELINE.md` or a fresh measurement if none exists yet;
- note: if an equivalent optimization or caching layer already exists,
  extend it and record the mapping in the completion report instead of
  creating a parallel implementation.

#### Implementation Contract
- the specific metric this Task targets (e.g. p95 latency, throughput, peak
  RSS, DB query count) and its unit;
- the workload this Task is measured against (input size, concurrency,
  warm/cold cache state) — must match or explicitly refine
  `BENCHMARK_BASELINE.md`'s Workload section;
- the acceptance threshold this Task must reach or move toward;
- invariants that must hold before and after (functional correctness, output
  equivalence, data freshness/consistency requirements);
- error categories this Task owns.

#### Detailed Implementation Steps
Numbered, concrete steps — not restatement of the Objective. Include, where
applicable:
1. inspect current implementation and existing profiling/benchmark output
   before writing an optimization — identify the actual bottleneck, not an
   assumed one;
2. confirm the contract above (metric, workload, threshold) before writing
   code;
3. implement only this Task's optimization — do not pull forward-Step scope
   in;
4. keep the optimization isolated enough to measure its individual
   contribution where practical (avoid bundling multiple unrelated changes
   into one immeasurable diff);
5. preserve existing correctness/output-equivalence — do not change result
   semantics to gain speed (no skipping validation, no returning stale/
   cached-but-wrong data, no silently reducing precision/completeness);
6. make failure/degradation behavior explicit under load (timeouts, backoff,
   circuit breaking) if this Task changes concurrency or I/O behavior;
7. add stable structured log context for the measured operation (timing,
   counts, no secrets);
8. add or update focused automated tests for correctness (the optimization
   must not regress functional behavior), plus a repeatable benchmark/load
   test for the targeted metric;
9. verify through the real owning code path under the defined workload, not
   only a microbenchmark in isolation, unless the Task explicitly is a
   microbenchmark-level unit.

#### Failure / Recovery Cases
List each realistic failure for this Task, including performance-specific
ones:
- optimization regresses correctness (wrong/stale/incomplete result) under
  some input this Task's happy-path testing did not cover;
- optimization improves the targeted metric but degrades another
  (e.g. lower latency but higher memory, higher throughput but higher error
  rate under load) — detection and acceptance/rejection decision;
- optimization's gain disappears or reverses under the full realistic
  workload/dataset size (works on the small fixture, not at scale);
- resource exhaustion or new contention introduced under concurrency this
  Task's change affects.

For each case, specify:
- error category/code;
- safe user-facing message (if user-facing);
- internal log context;
- retryability;
- cleanup/compensation action;
- final resulting state.

#### Task-Level Test Cases
- the success path (correctness preserved under representative input);
- each boundary condition relevant to this Task (empty/minimal input,
  maximum realistic input size, cold vs. warm cache);
- each failure case above;
- assert persisted/resulting state or output equivalence, not only that the
  benchmark ran — a faster wrong answer is a failed test;
- unit/correctness tests must not require live paid external providers
  unless explicitly marked as opt-in integration tests.

#### Evidence Required Before Checking This Task
- exact test/benchmark command(s) executed;
- PASS/FAIL result for correctness tests;
- **before/after measurement** for this Task's targeted metric — actual
  numbers under the defined workload, not just PASS/FAIL (e.g. "p95 420ms ->
  180ms over 500 requests, concurrency 20, warm cache");
- key artifact/state inspected;
- any deviation from this Task's contract and why it was necessary.

#### Task Done Condition
Implemented through the normal production code path, its main failure modes
are explicit, correctness tests pass, and the before/after measurement shows
the targeted metric moved toward (or reached) the acceptance threshold under
the defined workload. Placeholder code, mocks left in a production path,
unresolved TODOs, or an unmeasured "should be faster" claim do not satisfy
this condition.

<!-- Repeat Task N for every additional Task this Step requires. -->

## Task Execution Tracking

| Task | Code | Focused Tests | Integration Evidence | Verified |
|---|---|---|---|---|
| 1. <name> | [ ] | [ ] | [ ] | [ ] |

## Cross-Cutting Contracts

> See `shared/CROSS_CUTTING_CONTRACTS.md`. Include only sections relevant to
> this Step's actual behavior; do not leave an irrelevant section as `...`.
> For performance Steps, the Benchmark Contract below is mandatory whenever
> this Step makes or measures a performance change.

### Benchmark Contract

- **Workload definition**: exact input data, request mix, concurrency,
  dataset size, warm/cold cache state, and duration/iterations this Step
  measures against — must match or explicitly extend
  `BENCHMARK_BASELINE.md`;
- **Environment**: hardware/resources, runtime version, service
  dependencies, DB state, build mode (must be representative of production,
  not a debug build unless that is the explicit target);
- **Metric**: the exact metric(s) this Step reports (e.g. p95 latency,
  throughput, peak RSS, DB query count/time, cost/request);
- **Percentile / aggregation**: how the metric is aggregated (p50/p95/p99,
  mean, max) and over how many samples/iterations — a single-run number is
  not sufficient evidence;
- **Acceptance threshold**: the exact target value this Step must reach or
  move toward, taken from `BENCHMARK_BASELINE.md`'s Baseline table;
- **Explicit rejection criteria**: this Step's improvement is rejected if it
  is traceable to any of — skipping required work, caching invalid/stale
  results, disabling or weakening validation, using a smaller/unrealistic
  dataset than `BENCHMARK_BASELINE.md`'s Workload, removing error handling,
  or changing result semantics. State how this Step's measurement was
  checked against each of these before being accepted as a genuine
  improvement.

### Architecture Fit
...

### Expected Files / Modules
...

### Data / Persistence Changes
...

### API Contract
...

### Worker / Background Processing Contract
...

### Configuration / Environment
...

### Error Handling Matrix
...

### Logging / Observability
...

## Required Test Matrix

In addition to each Task's own tests, list Step-level tests that exercise
more than one Task together (end-to-end correctness regression suite, full
benchmark run under `BENCHMARK_BASELINE.md`'s defined workload, concurrency/
load test).

Correctness tests should not require live paid external APIs. Benchmark runs
against production-scale data are opt-in and must report whether they were
actually executed.

## Manual Verification

<Anything automated assertions cannot fully cover — visual responsiveness,
perceived latency, resource dashboards during a load test.>

## Regression / Compatibility Surface

- existing correctness tests and contracts that must keep passing after this
  Step's optimization;
- other metrics that must not regress even while the targeted metric
  improves (list them and their pre-Step values);
- ...

## Acceptance Criteria

- [ ] ...
- [ ] ...

## Implementation Review Checklist

> Baseline list from `shared/STEP_EXECUTION_PROTOCOL.md`; performance-
> specific items follow below the line.

- [ ] Existing repository architecture/behavior was inspected before changes.
- [ ] Only this Step's declared scope was implemented.
- [ ] New schemas/types are validated and versioned where necessary.
- [ ] Database migrations are present and tested when persistence changed.
- [ ] Long-running work runs outside request/response handlers.
- [ ] External commands/inputs are validated, not string-concatenated.
- [ ] Timeouts and failure paths are explicit for every external call.
- [ ] Retry behavior cannot silently duplicate or corrupt state/artifacts.
- [ ] Tests cover the core success path and each meaningful failure.
- [ ] Documentation/config examples were updated where relevant.
- [ ] Every Acceptance Criterion for this Step is independently verified.
- [ ] `CURRENT.md` was updated only after verification, not before.
- [ ] No Task or file belonging to a later Step/Gate was started.
---
- [ ] Baseline was measured under `BENCHMARK_BASELINE.md`'s defined workload
      before this Step's optimization was implemented.
- [ ] Before/after numbers are recorded for every Task, not just PASS/FAIL.
- [ ] Correctness/functional tests pass unchanged after the optimization.
- [ ] The improvement was checked against every Anti-Cheating Check in
      `BENCHMARK_BASELINE.md` and is not traceable to reduced work, disabled
      validation, a smaller dataset, or changed result semantics.
- [ ] Any metric that could trade off against the targeted metric (memory,
      error rate, other endpoints) was checked and did not regress.

## Step Execution Protocol

> See `shared/STEP_EXECUTION_PROTOCOL.md` for the full A–E protocol
> (Baseline -> Task Loop -> Step Integration -> Definition of Done -> Stop).
> This Step's Definition of Done additionally requires:

- every Task Execution Tracking row fully checked;
- this Step's own Acceptance Criteria and Implementation Review Checklist
  items verified, not assumed;
- before/after measurement evidence recorded for every Task and for this
  Step as a whole, under the workload defined in `BENCHMARK_BASELINE.md`;
- `CURRENT.md` updated to reflect completion only after the above.

## Completion

PASS:
1. mark this Step complete in `CURRENT.md`;
2. advance Current Target;
3. write the completion report (per `shared/EXECUTION_RULES.md`), including
   the before/after numbers and confirmation against the Anti-Cheating
   Checks;
4. STOP.

FAIL:
1. leave this Step incomplete;
2. do not advance Current Target;
3. report exact remediation needed, including whether the regression was in
   correctness or in a traded-off metric;
4. STOP.

Do not start the next Step or Gate in this invocation.
