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
2. every Step must follow `templates/STEP_TEMPLATE.md` in full — do not emit
   a thin summary. Each Step needs:
   - Required Reading / Existing System Inspection, including the relevant
     sections of `BENCHMARK_BASELINE.md`;
   - Tasks broken out per `shared/TASK_DECOMPOSITION_STANDARD.md` (Objective,
     Inspect Before Editing with concrete paths, Implementation Contract that
     names the specific metric/workload/threshold this Task targets,
     numbered Detailed Implementation Steps, Failure/Recovery Cases,
     Task-Level Test Cases, Evidence Required — including before/after
     numbers, not just PASS/FAIL, Task Done Condition);
   - a Task Execution Tracking table;
   - the relevant sections of `shared/CROSS_CUTTING_CONTRACTS.md`, plus the
     Benchmark Contract subsection `templates/STEP_TEMPLATE.md` requires
     (workload definition, environment, metric, percentile/aggregation,
     acceptance threshold, explicit rejection criteria for gains traceable
     to reduced work/disabled validation/stale data) — filled in, not left
     as placeholders;
   - the Regression / Compatibility Surface section;
   - the Implementation Review Checklist, performance-specific items
     included;
3. every Performance Optimization Gate must follow `templates/GATE_TEMPLATE.md`
   in full, per `shared/GATE_STANDARD.md` — including the full before/after
   comparison across every acceptance threshold, Correctness-Regression
   Verification, and the Anti-Cheating / Rejection Check;
4. `CURRENT.md` is authoritative;
5. PASS -> advance `CURRENT.md` -> completion report -> STOP;
6. FAIL -> do not advance -> remediation report -> STOP;
7. do not perform unrelated refactors or product changes;
8. include evidence and regression requirements in every Step;
9. do not start implementation while creating the plan.

A Step that is thin because the underlying work is genuinely small (a small,
well-isolated optimization with no persistence/API/worker surface) is
correct — omit inapplicable Cross-Cutting Contracts sections rather than
padding them. A Step that omits detail because it involves a real workload
change, persistence, API, worker, or correctness-sensitive behavior is not
acceptable.
