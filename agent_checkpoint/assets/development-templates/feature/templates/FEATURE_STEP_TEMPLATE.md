# Feature Step <ID> — <TITLE>

## Target
- Feature Change: <CHANGE-ID>
- Step: <ID>
- Scope: **Only this Step**

## Required Reading

Before implementing, read:
- this Feature's `CHANGE.md`
- this Feature's `IMPACT.md`
- root `AGENTS.md` / equivalent
- existing architecture / source-of-truth docs for the affected area
- existing tests for affected modules
- any domain-specific policy/spec doc the affected area owns

## Working Rule

Implement only this Step. If future work is relevant, leave a short TODO or
note only — do not implement it. This is an existing repository: inspect
current behavior/architecture before changing anything, per
`shared/CHANGE_SCOPE_RULES.md` and `shared/WORK_TYPE_HARD_RULES.md` (FEATURE).

## Goal

<Precise implementation goal — one or two sentences, not a restated title.>

## Preconditions

<Which earlier Step(s) must already be verified complete in `CURRENT.md`,
and which `IMPACT.md` findings this Step depends on.>

## Scope

### In Scope
- ...

### Out of Scope
- ...

## Implement

<High-level shape of the behavior this Step adds or changes — the "what,"
before the Task-by-Task "how" below. Reference the relevant `IMPACT.md`
findings (entry points, domain/services, persistence, UI, jobs/providers)
this Step touches.>

## Granular Execution Tasks

> Execute each Task in order and collect evidence before proceeding. See
> `shared/TASK_DECOMPOSITION_STANDARD.md` for the required structure of each
> Task below. Do not split a genuinely small Step into artificial Tasks —
> one Task is correct when the work is one coherent unit.

### Task 1 — <imperative, specific action>

#### Objective
...

#### Inspect Before Editing
- exact existing files/modules this Task extends or touches (from `IMPACT.md`);
- if an equivalent module already exists under a different path than assumed,
  extend it and record the mapping in the completion report instead of
  creating a parallel implementation;
- existing tests covering this area, so this Task's changes are checked
  against current expectations before they are edited.

#### Implementation Contract
- accepted inputs;
- returned outputs / persisted state;
- invariants that must hold before and after (including any existing
  invariant this Task must preserve);
- error categories this Task owns.

#### Detailed Implementation Steps
1. ...
2. ...

#### Failure / Recovery Cases
- ...
- For each: error category/code, safe user-facing message (if user-facing),
  internal log context, retryability, cleanup/compensation, final state.

#### Task-Level Test Cases
- the success path;
- each boundary condition relevant to this Task;
- each failure case above;
- assert persisted/resulting state or artifact, not only a return code;
- existing regression tests for this area, confirmed still passing;
- unit tests must not require live paid external providers unless explicitly
  marked as opt-in integration tests.

#### Evidence Required Before Checking This Task
- exact test/build command(s) executed;
- PASS/FAIL result;
- key artifact/state inspected (DB row, object metadata, API response,
  UI reload state, metrics, etc.);
- any deviation from this Task's contract and why it was necessary.

#### Task Done Condition
Implemented through the normal production code path, its main failure modes
are explicit, and its focused tests pass alongside existing regression tests
for the area it touches. Placeholder code, mocks left in a production path,
or unresolved TODOs do not satisfy this condition.

<!-- Repeat Task N for every additional Task this Step requires. -->

## Task Execution Tracking

| Task | Code | Focused Tests | Integration Evidence | Verified |
|---|---|---|---|---|
| 1. <name> | [ ] | [ ] | [ ] | [ ] |

## Cross-Cutting Contracts

> See `shared/CROSS_CUTTING_CONTRACTS.md`. Include only sections relevant to
> this Step's actual behavior; do not leave an irrelevant section as `...`.
> For each section that applies, state both the existing contract (from
> `IMPACT.md`) and what this Step changes.

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

## Regression Surface

- exact existing behaviors, endpoints, UI flows, jobs, or data paths this
  Step's change could affect, per `IMPACT.md`'s "Indirectly Affected" and
  "Must Remain Unchanged" findings;
- the specific existing test suite(s)/fixtures that exercise each of them;
- any behavior explicitly out of scope for this Step that must still pass
  unmodified.

## Required Test Matrix

In addition to each Task's own tests, list Step-level tests that exercise
more than one Task together, plus the existing regression suite(s) that
cover this Step's Regression Surface.

Unit tests should not require live paid external APIs. If a live-provider
check is required, make it an explicit opt-in integration test and report
whether it was actually executed.

## Manual Verification

<Anything automated assertions cannot fully cover — visual state, UX
timing, cross-device behavior, or existing-behavior spot checks.>

## Acceptance Criteria

- [ ] requested feature behavior works;
- [ ] existing behavior remains compatible (per Regression Surface);
- [ ] focused and regression tests pass;
- [ ] unrelated code was not modified unnecessarily;
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
- [ ] Existing regression tests for this Step's Regression Surface pass.
- [ ] Documentation/config examples were updated where relevant.
- [ ] Every Acceptance Criterion for this Step is independently verified.
- [ ] `CURRENT.md` was updated only after verification, not before.
- [ ] No Task or file belonging to a later Step/Gate was started.
---

## Step Execution Protocol

> See `shared/STEP_EXECUTION_PROTOCOL.md` for the full A–E protocol
> (Baseline -> Task Loop -> Step Integration -> Definition of Done -> Stop).
> This Step's Definition of Done additionally requires:

- every Task Execution Tracking row fully checked;
- this Step's own Acceptance Criteria and Implementation Review Checklist
  items verified, not assumed;
- the Regression Surface's existing tests re-run and passing;
- `CURRENT.md` updated to reflect completion only after the above.

## Completion

PASS:
1. mark this Step complete in `CURRENT.md`;
2. advance Current Target;
3. write the completion report (per `shared/EXECUTION_RULES.md`), noting any
   `IMPACT.md` findings that changed as a result of this Step;
4. STOP.

FAIL:
1. leave this Step incomplete;
2. do not advance Current Target;
3. report exact remediation needed;
4. STOP.

Do not start the next Step or Gate in this invocation.
