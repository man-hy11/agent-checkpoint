# Performance Optimization Gate — <TITLE>

## Preconditions

All planned Performance Optimization Steps are verified complete in
`CURRENT.md`. `BENCHMARK_BASELINE.md` exists and reflects the actual
workload/environment/metric used across all Steps (not only the original
plan).

## Gate Focus

verify reproducible before/after improvement under the defined workload
without correctness/resource regressions, and that no improvement is
traceable to reduced work, disabled validation, stale data, or unrealistic
fixtures.

## Verify

> See `shared/GATE_STANDARD.md`. Include only sections relevant to what this
> optimization work actually did; do not leave a relevant section as `...`.

### Primary Outcome
- every Step's Acceptance Criteria still hold when exercised together, not
  only individually;
- ...

### Before/After Comparison
- full before/after table across every acceptance threshold set in
  `BENCHMARK_BASELINE.md`'s Baseline table, with actual measured numbers
  (not "improved") for each metric;
- measurement taken under the exact workload/environment defined in
  `BENCHMARK_BASELINE.md`'s Workload and Environment sections — call out any
  deviation and why it is still representative;
- percentile/aggregation reported matches what `BENCHMARK_BASELINE.md`
  specifies (e.g. p95 over N samples), not a single best-case run;
- ...

### Correctness-Regression Verification
- full functional/correctness test suite for the affected code path passes
  after all Steps' optimizations combined, not only per-Step;
- output/result equivalence spot-checked against pre-optimization behavior
  on representative inputs;
- data freshness/consistency requirements from `BENCHMARK_BASELINE.md`'s
  Correctness Guard still hold;
- ...

### Anti-Cheating / Rejection Check
- explicitly confirm, metric by metric, that no improvement is traceable to
  any of `BENCHMARK_BASELINE.md`'s Anti-Cheating Checks: skipped required
  work, cached invalid/stale results, disabled/weakened validation, a
  smaller/unrealistic dataset, removed error handling, or changed result
  semantics;
- any metric whose improvement cannot be cleanly attributed to a legitimate
  optimization is treated as a Gate failure, not accepted on faith;
- ...

### Existing Behavior / Compatibility
- other endpoints/paths sharing the optimized resource (cache, connection
  pool, thread pool) were checked for contention/regression;
- ...

### Failure / Recovery
- each Step's Error Handling / Failure-Recovery Cases still behave as
  specified when triggered through the integrated system under load, not
  only in isolation;
- ...

### Security / Data / Operations
- ...

### Cross-Step Regression
- earlier Phases'/Steps' representative flows still pass;
- other metrics that were not the optimization target did not silently
  regress (memory, error rate, cost);
- ...

### Backward Compatibility
- ...

### Observability
- logging/correlation identifiers declared by this work's Steps are present
  in a real run, including timing/metric data used for the before/after
  comparison;
- ...

## Representative End-to-End

```text
entry point
-> workload defined in BENCHMARK_BASELINE.md executed against the
   optimized system
-> measured metric(s) meet or move toward the acceptance threshold
-> correctness/functional suite passes against the same run
-> surrounding/earlier behavior still works
```

## Required Evidence

- exact tests/benchmark commands executed;
- before measurement and after measurement, both under the same defined
  workload/environment (`before_measurement`, `after_measurement`);
- correctness-regression test results (`correctness_regression`);
- explicit confirmation against each Anti-Cheating Check;
- PASS/FAIL per verification area above;
- unresolved issues, explicitly named.

## Gate Failure

If the Gate reveals a defect:

1. do not mark the Gate complete;
2. do not patch large unrelated code inside the Gate — only tiny
   verification-only corrections are permitted, and only if this Gate
   explicitly allows them;
3. if the "improvement" is found to be traceable to a rejected cause (reduced
   work, disabled validation, stale data, unrealistic fixture), record the
   finding explicitly and treat this as a failed Gate, not a passed one with
   a caveat;
4. identify the required remediation as a new/reopened Step;
5. record evidence;
6. STOP.

## Gate PASS

1. mark the Performance Optimization Gate complete in `CURRENT.md`;
2. write the Gate report (per `shared/EXECUTION_RULES.md`), including the
   full before/after table and Anti-Cheating confirmation;
3. STOP.

Do not start unrelated further optimization in this invocation.
