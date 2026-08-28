# BENCHMARK_BASELINE.md

## Performance Question

What exactly is too slow/expensive?

## Metric

Examples:

- p50/p95/p99 latency;
- throughput;
- startup time;
- CPU;
- peak RSS/memory;
- DB query count/time;
- I/O;
- render/transcode duration;
- cost/request.

## Workload

Define:

- input data;
- request mix;
- concurrency;
- warm/cold state;
- cache state;
- dataset size;
- duration/iterations.

## Environment

- hardware/resources;
- runtime version;
- service dependencies;
- DB state;
- build mode;
- network assumptions.

## Baseline

| Metric | Baseline | Target |
|---|---:|---:|
| ... | ... | ... |

## Measurement Procedure

Exact commands/scripts.

## Correctness Guard

Performance work must continue to satisfy:

- functional tests;
- data correctness;
- auth/security;
- error handling;
- freshness/consistency requirements.

## Anti-Cheating Checks

Reject improvements caused by:

- skipping required work;
- caching invalid/stale results;
- disabling validation;
- using a smaller unrealistic dataset;
- removing error handling;
- changing result semantics.
