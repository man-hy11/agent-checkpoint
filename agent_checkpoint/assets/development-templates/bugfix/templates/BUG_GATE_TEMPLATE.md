# Bug Gate — <BUG TITLE>

## Preconditions

B1-B4 (or generated Bugfix Steps) are verified complete in `CURRENT.md`.

## Required Reading

- `BUG.md`;
- `CURRENT.md`;
- B1, B2, B3, B4 completion reports (reproduction, root cause, fix,
  regression evidence);
- `shared/GATE_STANDARD.md`.

## Verify

> See `shared/GATE_STANDARD.md`. Include only sections relevant to what
> this bugfix actually touched; do not leave a relevant section as `...`.

### Functional
- the original user-observed symptom from `BUG.md` no longer occurs when
  exercised end-to-end (not only via the unit-level regression test);
- `BUG.md`'s Fix Acceptance Summary criteria all hold when checked together,
  not only individually across separate Steps;
- ...

### Root Cause Alignment
- the implemented fix (B3) matches the evidence-backed root cause
  confirmed in B2, not merely the symptom;
- B2's minimal fix boundary was respected, or any deviation is explicitly
  recorded and justified;
- ...

### Regression Protection
- B3's regression test fails conceptually against the pre-fix behavior and
  passes against the fix (i.e. it is a real regression guard, not a test
  that would pass regardless);
- the regression test runs as part of the module's real, ordinarily
  executed test suite/command — not only as a standalone script that could
  be forgotten in future CI runs;
- ...

### Data / State
- schema/migrations touched by the fix (if any) are applied and consistent;
- existing persisted data from before the fix still loads/behaves
  correctly (backward compatibility), if the fix touched persistence;
- ...

### Security / Permissions
- the fix did not weaken any existing authorization/validation check;
- ...

### Failure / Recovery
- B3's Error Handling Matrix entries (if any) behave as specified when
  triggered through the integrated system, not only in isolation;
- ...

### Cross-Step Regression
- B4's verified adjacent/neighboring behavior still holds;
- other previously working flows that share the fixed code path still pass;
- ...

### Backward Compatibility
- external callers/consumers of any changed API/interface are not broken by
  the fix, or the break is an explicitly accepted, documented one;
- ...

### Observability
- logging/correlation identifiers relevant to the fixed path are present
  and sane in a real run (per B4's Operational Check);
- no new unexplained warning/error appears;
- ...

### Scope Audit
- no unrelated refactor, API change, or dependency upgrade was introduced
  across B1-B4;
- changed files are limited to B2's minimal fix boundary (plus the
  regression test), or deviations are explicitly justified;
- ...

## Representative End-to-End

```text
entry point (as a real user/caller would trigger it)
-> repeat the exact original bug scenario from BUG.md
-> expected observable result now occurs (bug no longer reproduces)
-> exercise at least one adjacent/neighboring behavior on the same code
   path (per B2's regression risk surface / B4's verified adjacent cases)
-> adjacent behavior still produces its correct, unchanged result
```

Run this against the real owning code path (actual API/UI/CLI entry point),
not only through the unit-level regression test in isolation.

## Required Evidence

- original reproduction result, re-run fresh at Gate time (PASS — symptom
  no longer occurs);
- regression test result (PASS, and confirmation it is wired into the
  real/ordinary test run, not a standalone script only);
- targeted/affected test suite result (PASS, or failures explicitly triaged
  as pre-existing and unrelated);
- adjacent/neighboring behavior result from B4, re-confirmed if practical;
- changed files list, cross-checked against B2's minimal fix boundary;
- any remaining limitations or known residual risk, named explicitly.

## Gate Failure

If the Gate reveals a defect:

1. do not mark the Bug Gate complete;
2. do not patch large unrelated code inside the Gate — only tiny
   verification-only corrections are permitted, and only if this Gate
   explicitly allows them;
3. identify the required remediation as a reopened B2 (if root cause was
   mis-scoped), B3 (if the fix itself is incomplete/incorrect), or B4 (if
   regression coverage/adjacent verification was insufficient);
4. record evidence;
5. STOP.

## Gate PASS

1. mark Bug Gate complete in `CURRENT.md`;
2. write the final bugfix summary (per `shared/EXECUTION_RULES.md`),
   including: original symptom, confirmed root cause, the fix, regression
   coverage added, and any residual known limitations;
3. STOP.

Do not begin any further work (new bug, follow-on feature, unrelated
cleanup) in this invocation.
