# STEP_EXECUTION_PROTOCOL.md

## Purpose

A Step is not "read the goal, write code, report done." This is the ordered
protocol every Step execution (`checkpoint-execute` / `checkpoint-verify-gate`)
follows, regardless of workflow type.

## A. Baseline

- read every document this Step's "Required Reading" lists;
- inspect the current code and git diff/status before writing anything;
- run the nearest existing tests/build to establish a baseline;
- record any pre-existing failure — do not silently attribute it to this
  Step, and do not silently fix unrelated pre-existing failures either.

## B. Task Loop

For each Task in order (see `TASK_DECOMPOSITION_STANDARD.md`):

1. implement only that Task's contract;
2. run its focused tests;
3. inspect the resulting state/artifact, not only exit codes;
4. fill that Task's row in the Task Execution Tracking table before moving
   to the next Task.

Do not start Task N+1's implementation before Task N's row is fully checked,
unless the Tasks are explicitly independent and the plan says so.

## C. Step Integration

After all Tasks are individually done:

- run the Step's end-to-end integration path (the real owning code path,
  not just unit tests in isolation);
- run relevant regression tests from earlier verified Steps that this Step's
  change could affect;
- inspect persistence/artifact/UI state manually wherever automated
  assertions cannot fully validate quality.

## D. Definition of Done

All of the following must hold before the Step may be marked complete:

- every Task is verified (all four tracking columns checked);
- every item in this Step's Acceptance Criteria is verified, not assumed;
- every item in this Step's Implementation Review Checklist is verified;
- configuration/docs affected by this Step are updated;
- no Task or code belonging to a later Step was implemented;
- the tracker (`CURRENT.md` / `PHASE.md` equivalent) is updated only after
  the above is true, never before.

## E. Stop

Write the completion report per `EXECUTION_RULES.md` and stop. Do not begin
the next Step or Gate in the same invocation.

## Implementation Review Checklist (baseline — extend per workflow type)

Before marking any Step complete, verify all applicable items:

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
- [ ] The tracker file was updated only after verification, not before.
- [ ] No Task or file belonging to a later Step/Gate was started.
