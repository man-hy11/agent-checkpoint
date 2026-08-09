# Usage Cheatsheet — 10 Work Types

## Choose

```text
New product/system                  -> project
Feature addition/change             -> feature
Bug correction                      -> bugfix
Internal restructure, same behavior -> refactor
Runtime/framework/dependency update -> upgrade
Database/data/schema change         -> migration
Latency/resource optimization       -> performance
External API/service connection     -> integration
Deployment/release                  -> release
Technical research/POC              -> spike
```

## Plan First

Example:

```text
Read performance/prompts/PLAN_PERFORMANCE_PROMPT.md
and create the work plan for this performance issue.
Do not implement it yet.
```

Each workflow also contains `QUICK_REQUEST.txt` with a ready-to-copy Korean request.

## Implement

First execution:

```text
Read the generated FIRST_RUN_PROMPT.md and proceed exactly as written.
```

Every later execution:

```text
Read the generated CONTINUE_PROMPT.md and proceed exactly as written.
```

No Step number editing is necessary when the generated tracker is maintained correctly.

## Universal State Flow

```text
Current Target
-> execute exactly one Step/Gate
-> tests + evidence
-> PASS?
   yes: tracker advance -> report -> STOP
   no:  tracker unchanged -> failure report -> STOP
```

## Important Special Rules

### BUGFIX
```text
Reproduce -> Evidence -> Root Cause -> Fix -> Regression
```

### REFACTOR
```text
Characterize behavior before risky restructuring.
No intended behavior change.
```

### UPGRADE
```text
Inventory -> Breaking changes -> Bounded upgrade -> Regression
```

### MIGRATION
```text
Data baseline -> Recovery design -> Forward migration -> Validate -> Restore/rollback evidence
```

### PERFORMANCE
```text
Baseline measurement before optimization.
Keep before/after numbers.
```

### INTEGRATION
```text
Auth + timeout + retry + rate limit + idempotency + provider outage.
```

### RELEASE
```text
Build success != deployment success.
Smoke + observability + rollback readiness required.
```

### SPIKE
```text
POC output is evidence/decision.
POC code is not automatically production code.
```
