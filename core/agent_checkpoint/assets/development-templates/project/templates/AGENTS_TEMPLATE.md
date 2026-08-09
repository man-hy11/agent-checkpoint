# AGENTS.md — Project Template

## Project Authority

Before implementation read:

1. `AGENTS.md`
2. `PHASE.md`
3. `docs/DEVELOPMENT_PLAN.md`
4. `docs/TASK_EXECUTION_STANDARD.md`
5. current Step/Gate prompt
6. every cross-cutting document referenced by the current target

## Authoritative Tracker

`PHASE.md` is the authoritative implementation progress tracker.

## Step Execution Hard Rule

One invocation may execute at most ONE Step or ONE Phase Gate.

After PASS:

1. mark current target complete;
2. advance `Current Target`;
3. produce completion report;
4. STOP.

Do not begin the newly selected target.

## Failure

If any required verification fails:

- do not mark complete;
- do not advance;
- document exact failure/remediation;
- STOP.

## Scope

Do not implement future scope unless the current Step explicitly requires a foundation/interface/contract.

## Project Invariants

The planning process must replace this section with project-specific invariants.

Do not retain irrelevant examples.
