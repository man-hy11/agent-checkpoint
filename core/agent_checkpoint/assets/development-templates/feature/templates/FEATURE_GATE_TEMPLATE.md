# Feature Gate — <FEATURE NAME>

## Preconditions

All Feature Steps are verified complete in `CURRENT.md`.

## Verify

> See `shared/GATE_STANDARD.md`. Include only sections relevant to what this
> Feature actually changed; do not leave a relevant section as `...`.

### Functional / New Feature
- every Step's Acceptance Criteria still hold when exercised together, not
  only individually;
- the behavior described in `CHANGE.md`'s Target Behavior is achieved;
- ...

### Existing Behavior / Regression
- every Regression Surface item named across this Feature's Steps still
  behaves as before, verified via the existing test suite(s)/fixtures that
  cover it, not only by inspection;
- `IMPACT.md`'s "Must Remain Unchanged" findings still hold end-to-end;
- ...

### Data / Migration
- schema/migrations introduced by this Feature are applied and consistent;
- existing data is preserved across the change;
- ...

### Security / Permissions
- existing authentication/authorization/data-ownership rules identified in
  `IMPACT.md` still hold for both new and existing code paths;
- ...

### UI / API Compatibility
- externally observable contracts (API shapes, error codes, UI states,
  copy) unaffected by this Feature are unchanged;
- contracts this Feature intentionally changed match `CHANGE.md`'s
  Backward Compatibility section;
- ...

### Cross-Step Regression
- each Step's Error Handling Matrix / Failure-Recovery entries still behave
  as specified when triggered through the integrated system, not only in
  isolation;
- earlier Steps' representative flows still pass together with later
  Steps' changes;
- ...

### Observability
- logging/correlation identifiers declared by this Feature's Steps are
  present in a real run;
- ...

## Representative End-to-End

```text
existing workflow entry point
-> Step-by-Step path through this Feature's new/changed behavior
-> expected observable result
-> existing surrounding behavior still works
```

## Required Evidence

- exact tests/commands executed;
- actual state/artifacts inspected (not just process exit codes);
- regression evidence for every Regression Surface item;
- PASS/FAIL per verification area above;
- changed files;
- unresolved issues, explicitly named.

## Gate Failure

If the Gate reveals a defect:

1. do not mark the Gate complete;
2. do not patch large unrelated code inside the Gate — only tiny
   verification-only corrections are permitted, and only if this Gate
   explicitly allows them;
3. identify the required remediation as a new/reopened Step in `CURRENT.md`;
4. record evidence;
5. STOP.

## Gate PASS

1. mark Feature Gate complete in `CURRENT.md`;
2. record the final Feature summary (what changed, what was preserved);
3. write the Gate report (per `shared/EXECUTION_RULES.md`);
4. STOP.

Do not begin unrelated cleanup or a new Feature in this invocation.
