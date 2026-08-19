# Phase <P> / Step <P-S> — <TITLE>

## Target
- Phase: <P>
- Step: <P-S>
- Scope: **Only this Step**

## Required Reading

Before implementing, read:
- `AGENTS.md`
- `PHASE.md`
- `docs/DEVELOPMENT_PLAN.md`
- `docs/ARCHITECTURE.md`
- `docs/DATA_CONTRACTS.md`
- `docs/TEST_STRATEGY.md`
- `docs/PRODUCT_UI_SPEC.md` when this Step affects user-facing workflow, state, or copy
- any domain-specific policy/spec doc this Step's area owns
- relevant existing source files and their current tests

## Working Rule

Implement only this Step. If future work is relevant, leave a short TODO or
note only — do not implement it.

## Goal

<Precise implementation goal — one or two sentences, not a restated title.>

## Preconditions

<Which earlier Step(s)/Gate(s) must already be verified complete.>

## Scope

### In Scope
- ...

### Out of Scope
- ...

## Implement

<High-level shape of the behavior this Step adds — the "what," before the
Task-by-Task "how" below.>

## Granular Execution Tasks

> Execute each Task in order and collect evidence before proceeding. See
> `shared/TASK_DECOMPOSITION_STANDARD.md` for the required structure of each
> Task below.

### Task 1 — <imperative, specific action>

#### Objective
...

#### Inspect Before Editing
- ...
- Inspect equivalent existing modules/tests if paths differ. Do not create a
  parallel layer merely to match this prompt.

#### Implementation Contract
- ...

#### Detailed Implementation Steps
1. ...
2. ...

#### Failure / Recovery Cases
- ...
- For each: error category/code, safe user-facing message, internal context,
  retryability, cleanup/compensation, final state.

#### Task-Level Test Cases
- ...
- Assert persisted/resulting state or artifact, not only the return code.
- Unit tests must avoid live paid providers unless explicitly opt-in.

#### Evidence Required Before Checking This Task
- exact test/build command(s) executed;
- PASS/FAIL result;
- key artifact/state inspected;
- any deviation from this Task's contract and why.

#### Task Done Condition
Implemented through the real production code path, main failure modes
explicit, focused tests pass. Placeholder/mocked-in-production/TODO does not
satisfy this.

<!-- Repeat Task N for every additional Task this Step requires. -->

## Task Execution Tracking

| Task | Code | Focused Tests | Integration Evidence | Verified |
|---|---|---|---|---|
| 1. <name> | [ ] | [ ] | [ ] | [ ] |

## Cross-Cutting Contracts

> See `shared/CROSS_CUTTING_CONTRACTS.md`. Include only sections relevant to
> this Step's actual behavior; do not leave an irrelevant section as `...`.

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
more than one Task together (integration/E2E fixtures, provider-failure
simulation, regression fixtures from earlier Steps).

Use `docs/TEST_STRATEGY.md`. Unit tests should not require live paid
external APIs. If a live-provider check is required, make it an explicit
opt-in integration test and report whether it was actually executed.

## Manual Verification

<Anything automated assertions cannot fully cover — visual state, UX
timing, cross-device behavior.>

## Product UI Acceptance

For all user-facing behavior introduced or changed in this Step:

- follow `docs/PRODUCT_UI_SPEC.md`;
- implement applicable loading, empty, populated, error, disabled, and
  processing states;
- do not expose functionality belonging to a later Phase as usable;
- preserve a clear next action for the user;
- verify save/reload behavior when this Step persists user state;
- verify layout at the project's supported breakpoints;
- surface stable backend error/status codes rather than parsed strings.

## Acceptance Criteria

- [ ] ...
- [ ] ...

## Implementation Review Checklist

> Baseline list from `shared/STEP_EXECUTION_PROTOCOL.md`; add Step-specific
> items below the line if this Step has additional invariants to protect.

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
- [ ] `PHASE.md` was updated only after verification, not before.
- [ ] No Task or file belonging to a later Step/Gate was started.
---

## Step Execution Protocol

> See `shared/STEP_EXECUTION_PROTOCOL.md` for the full A–E protocol
> (Baseline -> Task Loop -> Step Integration -> Definition of Done -> Stop).
> This Step's Definition of Done additionally requires:

- every Task Execution Tracking row fully checked;
- this Step's own Acceptance Criteria and Implementation Review Checklist
  items verified, not assumed;
- `PHASE.md` updated to reflect completion only after the above.

## Completion

PASS:
1. mark this Step complete in `PHASE.md`;
2. advance Current Target;
3. write the completion report (per `shared/EXECUTION_RULES.md`);
4. STOP.

FAIL:
1. leave this Step incomplete;
2. do not advance Current Target;
3. report exact remediation needed;
4. STOP.

Do not start the next Step or Gate in this invocation.
