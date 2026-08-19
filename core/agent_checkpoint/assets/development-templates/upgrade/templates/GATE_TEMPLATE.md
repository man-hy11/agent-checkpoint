# Upgrade Gate — <TITLE>

## Preconditions

All planned Upgrade Steps are verified complete in `CURRENT.md`.

## Gate Focus

Verify target versions, full compatibility-matrix closure, migration
adaptations, full regression, runtime startup, and rollback readiness across
the entire upgraded surface — not just each Step in isolation.

## Verify

> See `shared/GATE_STANDARD.md`. Include only sections relevant to what this
> upgrade actually changed; do not leave a relevant section as `...`.

### Version / Compatibility Verification
- every component in `COMPATIBILITY_MATRIX.md`'s Current -> Target table is
  at its declared target version, verified from the lockfile/manifest, not
  assumed;
- Runtime/Toolchain Requirements (OS/base image, compiler, runtime, DB
  client, CI, deployment) are satisfied in the actual build/deploy
  environment;
- ...

### Breaking-Change Closure
- every row in `COMPATIBILITY_MATRIX.md`'s Breaking Changes table has
  verified remediation evidence — no row is left unresolved, silenced by a
  disabled test, or worked around by an undocumented pin;
- every entry in Removed/Deprecated APIs has zero remaining references in
  the codebase (verified by search, not assumption);
- Transitive Dependency Concerns are resolved or explicitly accepted with
  justification;
- ...

### Existing Behavior / Compatibility
- ...

### Failure / Recovery
- each Step's Error Handling Matrix entries still behave as specified when
  triggered through the integrated system, not only in isolation;
- ...

### Security / Data / Operations
- data ownership, auth/authorization, and deployment constraints from
  `CHANGE_SCOPE_RULES.md` are preserved;
- ...

### Rollback Verification
- the Rollback Compatibility questions in `COMPATIBILITY_MATRIX.md` are
  answered with evidence, not assumption: can old application run against
  upgraded environment; can new application run against old environment;
  is DB/data format backward compatible; is downgrade actually supported;
- if a rollback path is not available, this is explicitly documented and
  was accepted as a deliberate risk, not an oversight;
- ...

### Cross-Step Regression
- the full existing test suite passes, not only tests for touched files;
- earlier verified Steps' behavior still holds when exercised together;
- ...

### Observability
- logging/correlation identifiers declared by this upgrade's Steps are
  present in a real run;
- ...

## Representative End-to-End

```text
clean install at target versions
-> build
-> startup/runtime smoke check
-> Step-by-Step path through upgraded behavior
-> expected observable result
-> surrounding/earlier behavior still works
```

## Required Evidence

- exact tests/commands executed, including clean install, build, full test
  suite, startup smoke check, and migrations where applicable;
- actual state/artifacts inspected (not just process exit codes);
- PASS/FAIL per verification area above;
- unresolved issues, explicitly named, including any Breaking Changes row
  still open.

## Gate Failure

If the Gate reveals a defect (including any unresolved Breaking Changes
row or missing rollback path):

1. do not mark the Gate complete;
2. do not patch large unrelated code inside the Gate — only tiny
   verification-only corrections are permitted, and only if this Gate
   explicitly allows them;
3. identify the required remediation as a new/reopened Upgrade Step;
4. record evidence;
5. STOP.

## Gate PASS

1. mark the Upgrade Gate complete in `CURRENT.md`;
2. write the Gate report (per `shared/EXECUTION_RULES.md`), including
   confirmation that every `COMPATIBILITY_MATRIX.md` row is closed and the
   rollback path status;
3. STOP.

Do not start unrelated cleanup or new work in this invocation.
