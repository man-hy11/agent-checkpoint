Use the supplied **AI Development Templates / Performance Optimization Template** to plan this work.

Do not execute the change yet.

First inspect the existing repository and gather the context needed to plan safely.

Create an independent work package such as:

```text
changes/PERF-YYYY-NNN-<slug>/
```

Create:

- `WORK.md` or a more specific work-description file;
- `CURRENT.md`;
- detailed Step prompts;
- `gate.md`;
- `FIRST_RUN_PROMPT.md`;
- `CONTINUE_PROMPT.md`.

Default conceptual Steps:

```text
P1 Baseline Measurement
P2 Bottleneck Analysis
P3 Optimization Experiment
P4 Production-Quality Optimization
P5 Before/After & Correctness Regression
Performance Optimization Gate
```

Adjust Step count to the actual complexity.

Planning focus:

improving latency, throughput, startup time, memory, CPU, I/O, database efficiency, rendering time, or resource cost

Hard rules:

- Measure before optimizing.
- Define workload, environment, metric, percentile/aggregation, and acceptance threshold.
- Do not optimize based only on intuition.
- Correctness must not regress for a faster benchmark.
- Keep before/after evidence.
- Watch for latency, throughput, memory, CPU, I/O, DB load, cache hit rate, and cost tradeoffs as relevant.
- Reject benchmark improvements caused by reduced work, disabled validation, stale data, or unrealistic fixtures.

Execution rules:

1. one invocation = one Performance Optimization Step or one Performance Optimization Gate;
2. PASS -> advance `CURRENT.md` -> completion report -> STOP;
3. FAIL -> do not advance -> remediation report -> STOP;
4. do not perform unrelated refactors or product changes;
5. include evidence and regression requirements in every Step;
6. do not start implementation while creating the plan.
