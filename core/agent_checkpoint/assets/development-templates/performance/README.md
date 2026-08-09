# Performance Optimization Template

Use this workflow for **improving latency, throughput, startup time, memory, CPU, I/O, database efficiency, rendering time, or resource cost**.

Recommended work package:

```text
changes/PERF-YYYY-NNN-<slug>/
```

Default lifecycle:

```text
P1 Baseline Measurement
-> P2 Bottleneck Analysis
-> P3 Optimization Experiment
-> P4 Production-Quality Optimization
-> P5 Before/After & Correctness Regression
-> Performance Gate
```

## Hard Rules

- Measure before optimizing.
- Define workload, environment, metric, percentile/aggregation, and acceptance threshold.
- Do not optimize based only on intuition.
- Correctness must not regress for a faster benchmark.
- Keep before/after evidence.
- Watch for latency, throughput, memory, CPU, I/O, DB load, cache hit rate, and cost tradeoffs as relevant.
- Reject benchmark improvements caused by reduced work, disabled validation, stale data, or unrealistic fixtures.

All execution uses:

```text
one AI invocation = one Step or one Gate
```

PASS advances `CURRENT.md` to the next target and then STOPs.
FAIL does not advance.
