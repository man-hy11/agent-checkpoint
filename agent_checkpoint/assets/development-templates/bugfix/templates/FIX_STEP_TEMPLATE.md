# Bugfix Step B3 — Minimal Fix

## Target
- Step: B3
- Scope: **Only this Step**

## Required Reading

Before implementing, read:
- existing repo agent instructions;
- `BUG.md`;
- `CURRENT.md`;
- B2's completion report: confirmed root cause, experiment evidence, and
  minimal fix boundary;
- the project's source-of-truth architecture/data-contract docs for the
  affected area, if any exist;
- relevant existing source files and their current tests within the fix
  boundary.

## Working Rule

Implement only the minimal fix defined by B2's boundary. If a broader
improvement seems warranted, leave a short TODO/note only — do not
implement it here. Per `shared/WORK_TYPE_HARD_RULES.md`'s BUGFIX rule:
reproduce -> prove root cause -> minimal fix -> regression. B1 and B2 are
already done; this Step is the minimal-fix link in that chain, not a
redesign opportunity.

## Goal

Implement the smallest correct fix for the evidence-backed root cause
confirmed in B2, guarded by a regression test, without expanding scope
beyond B2's minimal fix boundary.

## Preconditions

B1 and B2 verified complete. B2's minimal fix boundary (files/modules,
behavior changed, behavior preserved, regression risk) is available.

## Scope

### In Scope
- the files/modules named in B2's minimal fix boundary;
- the specific behavior change B2 identified as necessary to eliminate the
  root cause;
- a regression test that fails before the fix and passes after;
- verification via the original reproduction case from B1.

### Out of Scope
- anything outside B2's minimal fix boundary;
- unrelated refactors, API changes, or dependency upgrades;
- weakening validation to make a symptom disappear without addressing the
  confirmed cause;
- redesigning architecture "while in the area."

## Implement

<High-level shape of the fix — the "what," matching B2's minimal fix
boundary, before the Task-by-Task "how" below.>

## Granular Execution Tasks

> Execute each Task in order and collect evidence before proceeding. See
> `shared/TASK_DECOMPOSITION_STANDARD.md` for the required structure of each
> Task below.

### Task 1 — Add/Prepare Regression Test

#### Objective
Create a test that fails on the current (broken) behavior and will pass
once the fix is applied, directly protecting the confirmed root cause.

#### Inspect Before Editing
- existing test files/suites covering the affected module — extend an
  existing suite instead of creating a parallel one if a natural home
  exists;
- B1's minimized reproduction case and B2's experiment, both of which are
  strong candidates to convert directly into this regression test.

#### Implementation Contract
- accepted inputs: B1's reproduction case, B2's confirmed root cause and
  experiment;
- output: a new or extended automated test, currently failing;
- invariant: the test must fail for the same reason the bug occurs (i.e.
  it exercises the confirmed causal path), not for an unrelated reason.

#### Detailed Implementation Steps
1. locate the natural existing test suite for the affected module;
2. write a test that reproduces B1's minimized case (or converts B2's
   confirmed experiment) using the project's existing test conventions and
   fixtures;
3. run the test and confirm it fails, and that it fails via the same
   causal path identified in B2 (check the failure message/assertion, not
   just that it fails);
4. do not implement the fix yet in this Task.

#### Failure / Recovery Cases
- **New test fails for a different reason than the confirmed cause**:
  category `test-wrong-failure-mode`; log the actual failure vs. expected;
  not retryable without correcting the test; resulting state: revise the
  test until its failure matches B2's confirmed causal path before moving
  to Task 2.
- **Existing test suite conventions make direct reuse of B1's repro
  awkward** (e.g. different fixture format): category `test-fixture-gap`;
  log the adaptation made; resulting state: adapt the repro to the suite's
  conventions while preserving the same triggering condition — record the
  mapping.

#### Task-Level Test Cases
- the new/extended test fails before any fix code is written;
- the failure mode matches B2's confirmed causal path (assert on the
  specific error/state, not just "it throws").

#### Evidence Required Before Checking This Task
- exact test command executed;
- FAIL result (expected at this point) with the actual failure output;
- confirmation the failure matches B2's confirmed cause.

#### Task Done Condition
A regression test exists, currently fails, and its failure mode is
confirmed to match the evidence-backed root cause from B2 — not an
unrelated or superficial failure.

### Task 2 — Implement Fix

#### Objective
Change only the behavior identified in B2's minimal fix boundary to
eliminate the confirmed root cause.

#### Inspect Before Editing
- the exact files/modules named in B2's minimal fix boundary;
- current ownership of the affected behavior (types, persistence, side
  effects, callers, tests) before editing;
- note: if an equivalent module already exists under a different path than
  B2 assumed, extend it and record the mapping in the completion report
  instead of creating a parallel implementation.

#### Implementation Contract
- accepted inputs/outputs unchanged except for the specific behavior B2
  identified as needing to change;
- invariants: behavior B2 marked "preserved" must remain unchanged;
- error categories this fix owns: only those directly tied to the
  confirmed root cause.

#### Detailed Implementation Steps
1. confirm B2's minimal fix boundary once more before writing code;
2. implement only the identified behavior change — do not pull in
   unrelated cleanup or forward-looking scope;
3. keep the change's blast radius to the named files/modules; if
   implementation reveals the boundary was too narrow, stop and document
   why rather than silently expanding;
4. validate any external/boundary inputs touched by the fix before
   irreversible side effects, consistent with existing patterns in the
   module;
5. make partial-failure behavior explicit if the fix touches a
   multi-step operation;
6. add stable structured log context around the fixed path if the module
   already logs (no secrets);
7. do not weaken existing validation/assertions to make the symptom
   disappear — the fix must address the confirmed cause.

#### Failure / Recovery Cases
- **Fix requires touching a file/module outside B2's named boundary**:
  category `fix-boundary-exceeded`; log why; not silently done — stop and
  either justify the necessary minimal expansion explicitly in the
  completion report, or reconsider whether B2's root cause was correctly
  scoped; resulting state: do not proceed past this Task until the boundary
  question is resolved and recorded.
- **Fix would require weakening validation/error handling to pass**:
  category `symptom-masking-risk`; log the temptation and why it was
  rejected; resulting state: implement the real fix even if it is more
  work than suppressing the symptom.

#### Task-Level Test Cases
- covered by Task 1's regression test (now expected to pass) and Task 3's
  focused verification.

#### Evidence Required Before Checking This Task
- exact files changed;
- confirmation the change stayed within B2's boundary (or documented,
  justified deviation);
- any deviation from B2's contract and why it was necessary.

#### Task Done Condition
The fix is implemented through the normal production code path, stays
within B2's minimal fix boundary (or deviations are explicitly justified),
and does not weaken existing validation to mask the symptom.

### Task 3 — Focused Verification

#### Objective
Run the regression test and the original reproduction to confirm the fix
resolves the confirmed root cause.

#### Inspect Before Editing
- Task 1's regression test;
- B1's original minimized reproduction case.

#### Implementation Contract
- accepted inputs: the fix from Task 2;
- output: PASS on the regression test, PASS on re-running B1's original
  reproduction;
- invariant: both must be re-run against the actual fixed code path, not
  asserted from reading the diff.

#### Detailed Implementation Steps
1. run the regression test from Task 1 — confirm it now passes;
2. re-run B1's original reproduction case exactly (or as close as
   practical) — confirm the originally reported symptom no longer occurs;
3. run the directly affected module's existing test suite to catch
   immediate breakage;
4. if either check fails, return to Task 2 — do not adjust the test to
   force a pass.

#### Failure / Recovery Cases
- **Regression test passes but original B1 reproduction still fails**:
  category `fix-incomplete`; log both results; resulting state: the fix is
  not done — the regression test was not an accurate proxy for the real
  bug; return to Task 2 or reconsider Task 1's test.
- **Fix passes both checks but breaks an existing unrelated test**:
  category `fix-side-effect`; log the newly broken test and why; resulting
  state: do not silently adjust or delete the broken test — determine
  whether it reveals a real regression (return to Task 2) or a test that
  encoded the buggy behavior as expected (document explicitly, do not
  delete without justification).

#### Task-Level Test Cases
- Task 1's regression test: PASS;
- B1's original reproduction: PASS (symptom no longer occurs);
- directly affected module's existing suite: PASS, or failures explicitly
  triaged as pre-existing/unrelated.

#### Evidence Required Before Checking This Task
- exact test/reproduction commands executed;
- PASS/FAIL for each;
- triage notes for any pre-existing or newly surfaced unrelated failures.

#### Task Done Condition
The regression test and the original B1 reproduction both pass against the
actual fixed code, and any unrelated test breakage is explicitly triaged,
not ignored.

### Task 4 — Inspect Resulting State

#### Objective
Verify the actual resulting state/artifact the fix produces, not only that
the test process exited zero.

#### Inspect Before Editing
- whatever state the bug's symptom involved (DB row, API response, UI
  state, file/artifact output, log sequence) per B1's evidence.

#### Implementation Contract
- accepted inputs: the passing checks from Task 3;
- output: a recorded inspection of the actual state/artifact confirming
  the fix's effect, matching the evidence type captured in B1;
- invariant: inspection must use the real owning code path (actual DB
  query, actual API call, actual rendered UI), not a mock standing in for
  it.

#### Detailed Implementation Steps
1. identify which state/artifact type B1 used as evidence (DB row, API
   response, UI state, file output, log line);
2. inspect that same state/artifact type now, post-fix, through the real
   code path;
3. compare directly against B1's captured "actual" (now expected to no
   longer occur) and `BUG.md`'s "Expected Behavior";
4. record the inspected state as evidence.

#### Failure / Recovery Cases
- **Inspected state does not match expected behavior even though tests
  pass**: category `state-mismatch-despite-green-tests`; log the actual
  state observed; resulting state: the fix is not done — tests were
  insufficient; return to Task 2/Task 1 to close the gap.

#### Task-Level Test Cases
- the inspected state matches `BUG.md`'s Expected Behavior for the same
  scenario B1 reproduced.

#### Evidence Required Before Checking This Task
- the actual state/artifact inspected (not just exit codes);
- comparison against `BUG.md`'s Expected Behavior.

#### Task Done Condition
The real resulting state/artifact was inspected through the owning code
path and matches the documented expected behavior.

## Task Execution Tracking

| Task | Code | Focused Tests | Integration Evidence | Verified |
|---|---|---|---|---|
| 1. Add/Prepare Regression Test | [ ] | [ ] | [ ] | [ ] |
| 2. Implement Fix | [ ] | [ ] | [ ] | [ ] |
| 3. Focused Verification | [ ] | [ ] | [ ] | [ ] |
| 4. Inspect Resulting State | [ ] | [ ] | [ ] | [ ] |

## Cross-Cutting Contracts

> See `shared/CROSS_CUTTING_CONTRACTS.md`. Include only sections relevant to
> this fix's actual behavior; do not leave an irrelevant section as `...`.
> A minimal fix often touches few of these — omit what does not apply
> rather than padding it, but do not omit a section the fix actually
> touches.

### Architecture Fit
- name the source-of-truth architecture/data-contract doc(s) this fix must
  stay consistent with;
- confirm the fix extends existing structure per B2's boundary rather than
  introducing a parallel path.

### Expected Files / Modules
List the concrete files from B2's minimal fix boundary that this Step
actually touches.

### Data / Persistence Changes
If the fix changes any field/table/column or persisted value:
- exact fields/tables/columns affected, with types;
- migration required for any relational/schema change;
- existing data must be preserved across the change.
Omit if the fix does not touch persistence.

### API Contract
If the fix changes any endpoint/interface request/response shape or error
code:
- the exact before/after shape;
- whether this is a breaking change for existing callers, and how that is
  handled;
- stable machine-readable error codes (not parsed human-readable strings).
Omit if the fix does not touch an API/interface boundary.

### Worker / Background Processing Contract
If the fix touches long-running/asynchronous processing:
- how the confirmed root cause affected running/progress state;
- error classification (retryable vs non-retryable) as it relates to the
  fix;
- idempotency implications of the fix on retries.
Omit if the fix does not touch background/async processing.

### Configuration / Environment
If the fix introduces or changes a setting:
- typed/validated at startup or first use;
- documented where user-configurable;
- safe default only if one genuinely exists.
Omit if the fix introduces no configuration change.

### Error Handling Matrix
For each failure mode the fix introduces, changes, or was itself about:
- user-visible error code/message (if user-facing);
- internal log context;
- resulting record/job final state;
- retryability;
- cleanup/compensation behavior.
This section is rarely fully omittable for a bugfix — the bug itself was
very often an error-handling gap.

### Logging / Observability
- what changed in what gets logged at the fixed path, if anything;
- correlation identifiers preserved/added so this fix's activity remains
  traceable;
- reminder: never log credentials or full sensitive provider payloads.

## Constraints

Do not:
- redesign unrelated architecture;
- change unrelated APIs;
- upgrade dependencies without need;
- weaken validation;
- hide the symptom without addressing the confirmed cause;
- exceed B2's minimal fix boundary without explicit, recorded justification.

## Manual Verification

<Anything automated assertions cannot fully cover — visual state, UX
timing, cross-device behavior relevant to this fix.>

## Acceptance Criteria

- [ ] original B1 reproduction now passes;
- [ ] regression test passes and fails without the fix (confirmed in
      Task 1);
- [ ] fix matches the evidence-backed root cause from B2, not just the
      symptom;
- [ ] change surface remains within B2's minimal fix boundary, or
      deviation is explicitly justified;
- [ ] no known new failure introduced (existing suite checked, any breakage
      triaged);
- [ ] real resulting state/artifact inspected and matches `BUG.md`'s
      Expected Behavior.

## Implementation Review Checklist

> Baseline list from `shared/STEP_EXECUTION_PROTOCOL.md`; bugfix-specific
> items below the line.

- [ ] Existing repository architecture/behavior was inspected before
      changes.
- [ ] Only B2's minimal fix boundary was implemented.
- [ ] New schemas/types are validated and versioned where necessary.
- [ ] Database migrations are present and tested when persistence changed.
- [ ] Long-running work runs outside request/response handlers.
- [ ] External commands/inputs are validated, not string-concatenated.
- [ ] Timeouts and failure paths are explicit for every external call
      touched by the fix.
- [ ] Retry behavior cannot silently duplicate or corrupt state/artifacts.
- [ ] Tests cover the core success path and each meaningful failure tied to
      the fix.
- [ ] Documentation/config examples were updated where relevant.
- [ ] Every Acceptance Criterion for this Step is independently verified.
- [ ] `CURRENT.md` was updated only after verification, not before.
- [ ] No Task or file belonging to B4/Bug Gate was started.
- [ ] The fix addresses the confirmed root cause from B2, not merely the
      observed symptom.
- [ ] No unrelated refactor, API change, or dependency upgrade was
      introduced.
- [ ] No existing validation/error handling was weakened to make the
      symptom disappear.

---

## Step Execution Protocol

> See `shared/STEP_EXECUTION_PROTOCOL.md` for the full A-E protocol
> (Baseline -> Task Loop -> Step Integration -> Definition of Done -> Stop).
> This Step's Definition of Done additionally requires:

- every Task Execution Tracking row fully checked;
- this Step's own Acceptance Criteria and Implementation Review Checklist
  items verified, not assumed;
- `CURRENT.md` updated to reflect completion only after the above.

## Completion

PASS:
1. mark B3 complete in `CURRENT.md`;
2. advance Current Target to B4;
3. write the completion report (per `shared/EXECUTION_RULES.md`);
4. STOP.

FAIL:
1. leave B3 incomplete;
2. do not advance Current Target;
3. report exact remediation needed;
4. STOP.

Do not start B4 Regression work in this invocation.
