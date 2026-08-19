# Migration Gate — <TITLE>

## Preconditions

All planned Migration Steps are verified complete in `CURRENT.md`.
`MIGRATION_RECOVERY_PLAN.md` exists and reflects what was actually executed
(not only what was originally planned).

## Gate Focus

verify data correctness, application compatibility, forward path, retry
safety, and recovery/rollback evidence — with the rollback path having been
**actually exercised**, not merely documented.

## Verify

> See `shared/GATE_STANDARD.md`. Include only sections relevant to what this
> migration actually did; do not leave a relevant section as `...`.

### Functional
- every Step's Acceptance Criteria still hold when exercised together, not
  only individually;
- application code paths that read/write the migrated data behave correctly
  against the final migrated state;
- ...

### Data Integrity Verification
- row-count reconciliation between source and target across every migrated
  table/object, with the exact counts recorded (not "counts matched");
- invariant checks (required fields, uniqueness, referential integrity)
  re-run against the final state, not only during individual Steps;
- checksum/aggregate-total reconciliation where defined in
  `MIGRATION_RECOVERY_PLAN.md`;
- representative sample records spot-checked field-by-field against source;
- no orphaned, duplicated, or silently-dropped records;
- ...

### Rollback-Drill Verification
- the rollback/restore/compensation procedure defined in
  `MIGRATION_RECOVERY_PLAN.md` was **actually executed** in a non-production
  environment (or an equivalent verified mechanism) during this Gate or an
  earlier Step — record when and how;
- restored/rolled-back state was itself verified (not just "the restore
  command exited 0") — confirm row counts/invariants after restore;
- rollback trigger conditions from each Step's Failure/Recovery Cases are
  confirmed accurate against what was actually observed;
- if the migration is irreversible, this section instead records
  confirmation that the pre-migration backup exists, is restorable, and its
  restorability was actually tested;
- ...

### Existing Behavior / Compatibility
- consumers/writers of the affected data outside this migration's own code
  still function correctly against the final state;
- dual-read/dual-write compatibility window (if used) closed correctly, or
  is documented as still open with an explicit closing condition;
- ...

### Failure / Recovery
- each Step's Error Handling / Failure-Recovery Cases still behave as
  specified when triggered through the integrated system, not only in
  isolation;
- ...

### Security / Data / Operations
- access controls/ownership on migrated data are unchanged or correctly
  updated;
- sensitive fields were not exposed in migration logs/artifacts;
- ...

### Cross-Step Regression
- earlier, unrelated data flows still pass;
- ...

### Backward Compatibility
- ...

### Observability
- logging/correlation identifiers declared by this migration's Steps are
  present in a real run;
- ...

## Representative End-to-End

```text
entry point (application read/write against migrated data)
-> forward migration already applied
-> expected observable result matches target state
-> rollback path exercised against a disposable copy/environment
-> restored state verified
-> surrounding/earlier behavior still works
```

## Required Evidence

- exact tests/commands executed;
- row-count/invariant/checksum reconciliation output (source vs. target);
- rollback-drill execution log and post-restore verification output;
- PASS/FAIL per verification area above;
- unresolved issues, explicitly named.

## Sign-Off

- [ ] Data integrity check executed and recorded (`data_integrity_check`).
- [ ] Rollback/restore path actually exercised and verified
      (`rollback_verified`) — or, if irreversible, backup restorability
      confirmed.
- [ ] All destructive Steps ran only after `MIGRATION_RECOVERY_PLAN.md`
      existed and covered them.
- [ ] Named sign-off: who/what verified this Gate and when (`sign_off`).

## Gate Failure

If the Gate reveals a defect:

1. do not mark the Gate complete;
2. do not patch large unrelated code inside the Gate — only tiny
   verification-only corrections are permitted, and only if this Gate
   explicitly allows them;
3. if data integrity failed, trigger the rollback/compensation procedure
   from `MIGRATION_RECOVERY_PLAN.md` rather than attempting an ad hoc fix
   inside the Gate;
4. identify the required remediation as a new/reopened Step;
5. record evidence;
6. STOP.

## Gate PASS

1. mark the Migration Gate complete in `CURRENT.md`;
2. write the Gate report (per `shared/EXECUTION_RULES.md`), including the
   Sign-Off checklist above and a summary of the migration outcome;
3. STOP.

Do not start unrelated cleanup or further migrations in this invocation.
