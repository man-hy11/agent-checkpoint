# Migration Step <ID> — <TITLE>

## Target
- Step: <ID>
- Scope: **Only this Step**

## Goal

<Precise migration goal — one or two sentences, not a restated title.>

## Preconditions

<Which earlier Step(s)/Gate(s) must already be verified complete. Note if
`MIGRATION_RECOVERY_PLAN.md` must exist and be filled in before this Step may
run — no destructive Step may pass while it is absent or incomplete.>

## Required Reading / Existing System Inspection

Before implementing, read:
- repository agent instructions (`AGENTS.md` / `CLAUDE.md`);
- this work package (`WORK.md`);
- `CURRENT.md`;
- `MIGRATION_RECOVERY_PLAN.md` — source state, forward migration, backfill,
  validation, backup/restore, rollback/compensation, and cutover sections
  relevant to this Step;
- relevant source-of-truth architecture/data-contract docs;
- the current schema/format definition this Step touches (inspect the actual
  schema/migration history in the repository, not an assumed shape);
- existing migration tooling/framework already used in this repository —
  extend it rather than introducing a second migration mechanism;
- affected tests/contracts, and any existing backfill/migration scripts this
  Step's work extends or supersedes;
- current data volume and known invariants for the affected tables/objects
  (row counts, nullability, uniqueness, referential integrity) so this Step's
  validation has a real baseline to compare against.

## Scope

### In Scope
- ...

### Out of Scope
- ...

## Implement

<High-level shape of the migration behavior this Step adds — the "what,"
before the Task-by-Task "how" below. State explicitly whether this Step is
destructive (alters/deletes existing data or schema in place) or additive
(backfill into new columns/tables, dual-write) — this determines which
Failure/Recovery and Cross-Cutting sections below are mandatory.>

## Granular Execution Tasks

> Execute each Task in order and collect evidence before proceeding. See
> `shared/TASK_DECOMPOSITION_STANDARD.md` for the required structure of each
> Task below. For migration work, every Task that reads or writes persisted
> data must additionally satisfy the data-safety requirements below.

### Task 1 — <imperative, specific action>

#### Objective
...

#### Inspect Before Editing
- exact files/modules/migration scripts this Task is expected to touch or
  extend;
- current row/object counts and invariants for any table/collection this
  Task reads or writes;
- note: if an equivalent migration script or backfill job already exists,
  extend it and record the mapping in the completion report instead of
  creating a parallel implementation.

#### Implementation Contract
- accepted inputs (source rows/objects, schema version, batch boundaries);
- returned outputs / persisted state (target rows/objects, migration
  checkpoint/cursor state);
- invariants that must hold before and after (row counts, referential
  integrity, uniqueness, required fields, checksums/aggregate totals — name
  the specific ones this Task is responsible for);
- idempotency/restart-safety statement: what happens if this Task's
  migration/backfill is re-run or resumed after a partial failure — it must
  not duplicate or corrupt data;
- error categories this Task owns.

#### Detailed Implementation Steps
Numbered, concrete steps — not restatement of the Objective. Include, where
applicable:
1. inspect current schema/format, migration tooling, and existing
   consumers/writers before adding new modules or scripts;
2. confirm the contract above, including the idempotency statement, before
   writing migration code;
3. implement only this Task's forward-migration/backfill behavior — do not
   pull forward-Step scope (e.g. cutover, cleanup of the old shape) in;
4. define and implement checkpointing/batching so a partial run can resume
   without reprocessing already-migrated rows;
5. validate every batch's boundary/invariants before committing it, not only
   at the end of the full run;
6. make partial-failure behavior explicit — the system must end in a state
   that can be inspected and safely retried, resumed, or rolled back per
   `MIGRATION_RECOVERY_PLAN.md`;
7. add stable structured log context (batch id, row/object id range, no
   secrets or full PII payloads);
8. add focused automated tests for success, boundary conditions
   (empty/duplicate/malformed source rows), and meaningful failures;
9. verify through the real owning migration path (actual migration
   runner/script), not only in isolation against fixture data.

#### Failure / Recovery Cases
List each realistic failure for this Task. Cover at minimum, where this Task
is destructive or writes persisted data:
- partial-migration failure mid-batch (process killed, DB connection lost,
  timeout) — resulting state, and whether resume or restart-from-checkpoint
  is safe;
- rollback trigger condition specific to this Task (e.g. validation count
  mismatch beyond tolerance, checksum failure, referential integrity
  violation) and the rollback/compensation action taken, referencing
  `MIGRATION_RECOVERY_PLAN.md`;
- data-integrity violation detected post-write (orphaned reference, null in
  a required field, duplicate where uniqueness is required) — detection
  method and remediation;
- source data shape this Task did not anticipate (malformed/legacy record) —
  whether it is skipped, quarantined, or fails the batch, and how that is
  recorded.

For each case, specify:
- error category/code;
- safe user-facing message (if user-facing);
- internal log context;
- retryability;
- cleanup/compensation action;
- final resulting state.

#### Task-Level Test Cases
- the success path (representative batch of real-shaped data);
- each boundary condition relevant to this Task (empty batch, single row,
  max batch size, duplicate keys, null/missing optional fields);
- each failure case above, including a simulated mid-batch failure and
  resume;
- assert persisted/resulting state (row counts, specific field values,
  referential integrity, checksums) — not only a return code or exit status;
- unit tests must not require a live production database or destroy real
  data; use a disposable/test database or transaction rollback.

#### Evidence Required Before Checking This Task
- exact test/migration command(s) executed;
- PASS/FAIL result;
- key artifact/state inspected (row counts before/after, sample record diff,
  checksum, referential integrity check output);
- any deviation from this Task's contract and why it was necessary.

#### Task Done Condition
Implemented through the normal production migration path, its main failure
and rollback modes are explicit, and its focused tests pass. Placeholder
code, mocks left in a production migration path, or unresolved TODOs do not
satisfy this condition.

<!-- Repeat Task N for every additional Task this Step requires. -->

## Task Execution Tracking

| Task | Code | Focused Tests | Integration Evidence | Verified |
|---|---|---|---|---|
| 1. <name> | [ ] | [ ] | [ ] | [ ] |

## Cross-Cutting Contracts

> See `shared/CROSS_CUTTING_CONTRACTS.md`. Include only sections relevant to
> this Step's actual behavior; do not leave an irrelevant section as `...`.
> For migration Steps, Data / Persistence Changes is mandatory whenever this
> Step reads or writes persisted data, and must be filled in at the depth
> below — not the shared template's generic wording.

### Architecture Fit
...

### Expected Files / Modules
...

### Data / Persistence Changes

- exact fields/tables/columns/objects added, changed, or migrated, with
  types and nullability;
- migration script(s) this Step adds or extends, and how they are invoked in
  this repository's actual migration tooling;
- **row-count / invariant / checksum validation**: name the exact
  counts/invariants/checksums this Step verifies before and after (e.g.
  `SELECT COUNT(*)` per table pre/post, aggregate sum reconciliation, sampled
  checksum comparison) and the tolerance for any expected divergence;
- **idempotency / restart-safety statement**: explicit confirmation that
  re-running or resuming this Step's migration/backfill after a partial
  failure does not duplicate or corrupt data — state the mechanism
  (checkpoint table, upsert-by-key, transactional batch, etc.);
- **rollback procedure**: reference the exact section of
  `MIGRATION_RECOVERY_PLAN.md` that covers this Step's rollback/compensation
  path; if this Step is irreversible, say so explicitly and confirm the
  backup taken before this Step ran covers it;
- existing data must be preserved across the change unless this Step's
  explicit goal is deletion, in which case the deletion is backed by a
  verified backup;
- version any JSON/contract whose future reinterpretation could silently
  break older records.

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
more than one Task together (full migration dry-run against a
representative/anonymized dataset copy, resume-after-failure simulation,
validation-script run against the migrated result).

Unit tests should not require a live production database. If a run against a
production-like copy is required, make it an explicit opt-in step and report
whether it was actually executed.

## Manual Verification

<Anything automated assertions cannot fully cover — spot-checking sample
records, reviewing migration logs for unexpected warnings, confirming
downstream consumers still read correctly.>

## Regression / Compatibility Surface

- existing readers/writers of the affected data that must keep working
  during and after this Step (old code paths, other services, reporting
  jobs);
- compatibility window, if old and new shapes must coexist (dual-read/
  dual-write), and how long/under what condition that window closes;
- ...

## Acceptance Criteria

- [ ] ...
- [ ] ...

## Implementation Review Checklist

> Baseline list from `shared/STEP_EXECUTION_PROTOCOL.md`; migration-specific
> items follow below the line.

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
- [ ] `MIGRATION_RECOVERY_PLAN.md` exists and covers this Step before any
      destructive change ran.
- [ ] Row-count/invariant/checksum validation was actually executed and its
      output recorded, not assumed.
- [ ] This Step's idempotency/restart-safety statement was exercised (a
      resume-after-failure or re-run test was actually performed).
- [ ] Rollback/compensation path for this Step was confirmed to exist and
      match `MIGRATION_RECOVERY_PLAN.md` — not merely described.
- [ ] Backup was taken and its restorability confirmed before any
      irreversible/destructive action in this Step.
- [ ] Existing readers/writers of the affected data were identified and
      their continued correctness verified, not assumed.

## Step Execution Protocol

> See `shared/STEP_EXECUTION_PROTOCOL.md` for the full A–E protocol
> (Baseline -> Task Loop -> Step Integration -> Definition of Done -> Stop).
> This Step's Definition of Done additionally requires:

- every Task Execution Tracking row fully checked;
- this Step's own Acceptance Criteria and Implementation Review Checklist
  items verified, not assumed;
- row-count/invariant/checksum validation evidence recorded for every
  destructive or backfilling Task;
- `CURRENT.md` updated to reflect completion only after the above.

## Completion

PASS:
1. mark this Step complete in `CURRENT.md`;
2. advance Current Target;
3. write the completion report (per `shared/EXECUTION_RULES.md`), including
   the row-count/invariant/checksum evidence and idempotency evidence;
4. STOP.

FAIL:
1. leave this Step incomplete;
2. do not advance Current Target;
3. report exact remediation needed, including whether rollback per
   `MIGRATION_RECOVERY_PLAN.md` was triggered;
4. STOP.

Do not start the next Step or Gate in this invocation.
