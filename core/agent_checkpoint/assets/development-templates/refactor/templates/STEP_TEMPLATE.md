# Refactor Step <ID> — <TITLE>

## Target
- Step: <ID>
- Scope: **Only this Step**

## Goal

<Precise structural-change goal — one or two sentences. State the internal
design improvement, not a restated title. Intended external behavior does
not change unless this Step's parent work package explicitly declares a
behavior change, in which case that change belongs in FEATURE/BUGFIX scope
instead — see `WORK_TYPE_HARD_RULES.md`'s REFACTOR rule.>

## Preconditions

<Which earlier Step(s)/Gate must already be verified complete, including
whether `CHARACTERIZATION_BASELINE.md` for the affected surface already
exists and is current. A risky structural change must not start before its
characterization coverage exists.>

## Required Reading / Existing System Inspection

Before implementing, read:
- repository agent instructions (`AGENTS.md`/`CLAUDE.md` equivalent);
- this work package (`WORK.md`);
- `CURRENT.md`;
- `CHARACTERIZATION_BASELINE.md` — the frozen observable behavior this Step
  must not change;
- relevant source-of-truth architecture/docs;
- the exact modules/files this Step will restructure, and their current
  callers/consumers;
- affected tests/contracts, including tests that assert on internals this
  Step is about to move.

Inspect, concretely, before writing any code:
- current ownership boundaries of the code being restructured (who calls
  it, what depends on it, what it depends on);
- existing test coverage for the affected surface — if coverage is thin,
  add characterization tests before the structural change, not after;
- whether an equivalent module already exists under a different path; if so,
  extend/move it and record the mapping in the completion report instead of
  creating a parallel implementation.

## Scope

### In Scope
- ...

### Out of Scope
- ...
- any behavior change, however small — route it to a FEATURE or BUGFIX work
  package instead of folding it into this refactor.

## Implement

<High-level shape of the structural change this Step makes — the "what" and
"why" of the design improvement — before the Task-by-Task "how" below.>

## Granular Execution Tasks

> Execute each Task in order and collect evidence before proceeding. See
> `shared/TASK_DECOMPOSITION_STANDARD.md` for the required structure of each
> Task below. Frame each Task around a structural change with an explicit
> behavior-preservation contract: the Task's Implementation Contract must
> state which existing observable behavior is being preserved, and its
> Task-Level Test Cases must include the relevant characterization tests
> passing unchanged.

### Task 1 — <imperative, specific structural action>

#### Objective
One sentence: what this Task alone restructures, and what behavior it must
leave unchanged.

#### Inspect Before Editing
- exact files/modules this Task is expected to touch or move;
- current callers/consumers of the code being restructured;
- note: if an equivalent module already exists under a different path,
  extend/move it and record the mapping in the completion report instead of
  creating a parallel implementation.

#### Implementation Contract
- accepted inputs (unchanged from before this Task unless declared);
- returned outputs / persisted state (unchanged from before this Task unless
  declared);
- invariants that must hold before and after — this is the
  behavior-preservation contract for this Task specifically;
- error categories this Task owns.

#### Detailed Implementation Steps
1. run the characterization/regression tests covering this Task's surface
   and confirm they pass before making any change (baseline);
2. inspect current ownership (types, persistence, side effects, callers,
   tests) before moving or renaming anything;
3. confirm the behavior-preservation contract above before writing code;
4. make the structural change only — do not change externally observable
   behavior, and do not pull forward-Task/forward-Step scope in;
5. keep orchestration separate from low-level adapters so core logic is
   unit-testable without network/DB/browser/paid-provider dependencies
   where practical;
6. update all call sites/imports affected by the move; do not leave a
   duplicate/parallel implementation behind;
7. make partial-failure behavior explicit — the system must end in a state
   that can be inspected and safely retried or corrected;
8. add stable structured log context (no secrets);
9. re-run the characterization/regression tests from step 1 and confirm
   they still pass unchanged;
10. verify through the real owning code path, not only in isolation.

#### Failure / Recovery Cases
List each realistic failure for this Task (including "characterization test
regressed" as a first-class case). For each one, specify:
- error category/code;
- safe user-facing message (if user-facing);
- internal log context;
- retryability;
- cleanup/compensation action;
- final resulting state.

#### Task-Level Test Cases
- the full set of characterization tests covering this Task's surface,
  passing unchanged before and after;
- each boundary condition relevant to this Task;
- each failure case above;
- assert persisted/resulting state or artifact, not only a return code;
- unit tests must not require live paid external providers unless
  explicitly marked as opt-in integration tests.

#### Evidence Required Before Checking This Task
- exact test/build command(s) executed;
- PASS/FAIL result, including the pre-change baseline run and the
  post-change confirmation run;
- key artifact/state inspected (diff of moved code, characterization test
  output, API response, DB row, etc.);
- any deviation from this Task's behavior-preservation contract and why it
  was necessary — deviations must be flagged loudly, not buried.

#### Task Done Condition
Implemented through the normal production code path, no duplicate/parallel
implementation left behind, characterization tests for this Task's surface
pass unchanged, and its focused tests pass. Placeholder code, mocks left in
a production path, or unresolved TODOs do not satisfy this condition.

<!-- Repeat Task N for every additional Task this Step requires. -->

## Task Execution Tracking

| Task | Code | Focused Tests | Integration Evidence | Verified |
|---|---|---|---|---|
| 1. <name> | [ ] | [ ] | [ ] | [ ] |

## Cross-Cutting Contracts

> See `shared/CROSS_CUTTING_CONTRACTS.md`. Include only sections relevant to
> this Step's actual structural change; do not leave an irrelevant section
> as `...`. For a refactor, each section below should additionally state
> what is explicitly NOT changing.

### Architecture Fit
- name the source-of-truth architecture doc this restructuring must align
  with;
- state that listed file paths are recommended targets, not a command to
  restructure working code beyond this Step's declared scope — if an
  equivalent module already exists, extend/move it and record the mapping.

### Expected Files / Modules
- concrete paths this Step creates, moves, merges, or removes.

### Data / Persistence Changes
- state explicitly if none (the common case for a pure refactor);
- if schema/storage shape changes as a structural side effect, the
  persisted data's meaning/semantics must remain byte-for-byte or
  documented-compatible, and a migration is required per
  `CROSS_CUTTING_CONTRACTS.md`.

### API Contract
- state explicitly if no request/response shape changes;
- if only the internal implementation behind an endpoint changes, confirm
  request/response shape, status codes, and error codes are unchanged.

### Worker / Background Processing Contract
- state explicitly if not applicable;
- if background jobs are being restructured, confirm job state transitions,
  retry semantics, and idempotency are unchanged.

### Configuration / Environment
- state explicitly if no new/changed configuration;
- any renamed internal config keys must keep a compatible external
  interface or be called out as an explicit breaking change (out of scope
  for a pure refactor).

### Error Handling Matrix
- list each failure mode touched by this Step's restructuring, confirming
  error category, user-facing message, retryability, and cleanup behavior
  are unchanged from the pre-refactor baseline.

### Logging / Observability
- what changes in log location/call site vs. what stays the same in content
  and correlation identifiers;
- explicit reminder: never log credentials or full sensitive provider
  payloads.

## Regression / Compatibility Surface

- exact characterization tests (from `CHARACTERIZATION_BASELINE.md`) that
  cover this Step's affected surface;
- other existing tests/contracts that could be affected by this move even
  if not directly touched;
- any public/API/data contract this Step must leave byte-for-byte
  unchanged.

## Required Test Matrix

In addition to each Task's own tests, list Step-level tests that exercise
more than one Task together, and the full characterization/regression suite
run for the affected surface (not just the touched files).

## Manual Verification

<Anything automated assertions cannot fully cover for this structural
change — e.g. confirming no behavioral drift in a UI flow, timing-sensitive
paths, or cross-service call sequencing.>

## Acceptance Criteria

- [ ] ...
- [ ] All characterization tests for this Step's affected surface pass
      unchanged.
- [ ] No externally observable behavior changed outside what this Step
      explicitly declares.

## Implementation Review Checklist

> Baseline list from `shared/STEP_EXECUTION_PROTOCOL.md`; the items below
> the line are refactor-specific and must also be verified.

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
- [ ] `CURRENT.md` was updated only after verification, not before.
- [ ] No Task or file belonging to a later Step/Gate was started.
---
- [ ] Characterization tests existed (or were added) for this Step's
      affected surface BEFORE the structural change began.
- [ ] The full characterization/regression suite for the affected surface
      passes unchanged after the change, not merely a narrowed subset.
- [ ] No duplicate/parallel implementation was left behind after a
      move/merge — old call sites were updated, not shadowed.
- [ ] No unrelated feature work or bug fix was folded into this refactor.
- [ ] Any accidental behavior change discovered during the Step was
      reverted or explicitly escalated to a new FEATURE/BUGFIX unit — not
      silently kept.

## Step Execution Protocol

> See `shared/STEP_EXECUTION_PROTOCOL.md` for the full A–E protocol
> (Baseline -> Task Loop -> Step Integration -> Definition of Done -> Stop).
> This Step's Definition of Done additionally requires:

- every Task Execution Tracking row fully checked;
- the pre-change characterization/regression baseline was captured and the
  post-change run matches it;
- this Step's own Acceptance Criteria and Implementation Review Checklist
  items verified, not assumed;
- `CURRENT.md` updated to reflect completion only after the above.

## Completion

PASS:
1. mark this Step complete in `CURRENT.md`;
2. advance Current Target;
3. write the completion report (per `shared/EXECUTION_RULES.md`);
4. STOP.

FAIL:
1. leave this Step incomplete;
2. do not advance Current Target;
3. report exact remediation needed;
4. STOP.

Do not start the next Step or Gate in this invocation.
