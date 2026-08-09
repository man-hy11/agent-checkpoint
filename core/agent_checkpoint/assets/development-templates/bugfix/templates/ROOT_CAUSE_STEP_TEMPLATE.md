# Bugfix Step B2 — Root Cause Analysis

## Goal

Identify and support the actual root cause with evidence.

## Hard Rule

Do not proceed to B3 merely because a hypothesis sounds plausible.

The root cause must be supported by evidence such as:

- traced code path;
- failing/passing controlled experiment;
- state transition proof;
- log sequence;
- minimal test demonstrating causality;
- configuration/data comparison.

## Tasks

### Task 1 — Trace Failure Path
Identify the exact path from trigger to failure.

### Task 2 — Evaluate Hypotheses
List plausible causes and eliminate unsupported ones.

### Task 3 — Confirm Root Cause
Run a targeted experiment/test that supports the cause.

### Task 4 — Define Minimal Fix Boundary
Specify:
- files/modules;
- behavior changed;
- behavior preserved;
- regression risk.

## Acceptance Criteria

- [ ] root cause is evidence-backed;
- [ ] alternative major hypotheses are addressed;
- [ ] minimal fix boundary is explicit;
- [ ] no broad unrelated refactor is required without justification.

## Completion

PASS -> advance to B3 -> report -> STOP.

If root cause remains uncertain, do not advance.
