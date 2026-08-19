# Phase <P> Gate — <TITLE>

## Preconditions

All Phase <P> Steps are verified complete in `PHASE.md`.

## Verify

> See `shared/GATE_STANDARD.md`. Include only sections relevant to what this
> Phase actually built; do not leave a relevant section as `...`.

### Functional
- every Step's Acceptance Criteria still hold when exercised together, not
  only individually;
- ...

### Data / State
- schema/migrations for this Phase are applied and consistent;
- invariants declared across this Phase's Steps still hold end-to-end;
- ...

### Security / Permissions
- ...

### Failure / Recovery
- each Step's Error Handling Matrix entries still behave as specified when
  triggered through the integrated system, not only in isolation;
- ...

### Cross-Step Regression
- earlier Phases' representative flows still pass;
- ...

### Backward Compatibility
- ...

### Observability
- logging/correlation identifiers declared by this Phase's Steps are present
  in a real run;
- ...

## Representative End-to-End

```text
entry point
-> Step-by-Step path through this Phase's new behavior
-> expected observable result
-> surrounding/earlier behavior still works
```

## Required Evidence

- exact tests/commands executed;
- actual state/artifacts inspected (not just process exit codes);
- PASS/FAIL per verification area above;
- unresolved issues, explicitly named.

## Gate Failure

If the Gate reveals a defect:

1. do not mark the Gate complete;
2. do not patch large unrelated code inside the Gate — only tiny
   verification-only corrections are permitted, and only if this Gate
   explicitly allows them;
3. identify the required remediation as a new/reopened Step;
4. record evidence;
5. STOP.

## Gate PASS

1. mark Phase <P> Gate complete in `PHASE.md`;
2. advance Current Target to the next Phase's first Step;
3. write the Gate report (per `shared/EXECUTION_RULES.md`), including a
   Phase summary;
4. STOP.

Do not start the next Phase's Steps in this invocation.
