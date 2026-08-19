# Refactor Gate — <TITLE>

## Preconditions

All planned Refactor Steps are verified complete in `CURRENT.md`.

## Gate Focus

Prove behavior compatibility, architectural improvement, full regression
coverage, and the absence of unintended public/API/data changes across the
entire restructured surface — not just each Step in isolation.

## Verify

> See `shared/GATE_STANDARD.md`. Include only sections relevant to what this
> refactor actually restructured; do not leave a relevant section as `...`.

### Primary Outcome — Architectural Improvement
- the intended structural/design improvement is actually present in the
  final code (ownership boundaries, modularity, duplication removed, etc.)
  — name the concrete before/after;
- no duplicate/parallel implementation was left behind from any Step's
  move/merge;
- `WORK.md`'s Target State is achieved;
- ...

### Existing Behavior / Compatibility
- every characterization test in `CHARACTERIZATION_BASELINE.md` passes
  unchanged when run against the fully integrated result, not only per-Step;
- all public/API/data contracts declared frozen in
  `CHARACTERIZATION_BASELINE.md` are verified byte-for-byte or
  documented-compatible;
- ...

### Failure / Recovery
- each Step's Error Handling Matrix entries still behave as specified when
  triggered through the integrated system, not only in isolation;
- ...

### Security / Data / Operations
- data ownership, auth/authorization, and deployment constraints from
  `CHANGE_SCOPE_RULES.md` are preserved;
- ...

### Cross-Step Regression
- the full existing test suite passes, not only tests for the touched
  files;
- earlier verified Steps' behavior still holds when exercised together;
- ...

### Backward Compatibility
- any consumer of the restructured code (internal callers, external API
  clients, stored data) still functions without modification, unless a
  compatibility break was explicitly declared and routed to FEATURE/BUGFIX
  scope;
- ...

### Observability
- logging/correlation identifiers declared by this refactor's Steps are
  present in a real run and equivalent in content to the pre-refactor
  baseline;
- ...

## Representative End-to-End

```text
entry point
-> Step-by-Step path through the restructured surface
-> expected observable result (identical to pre-refactor baseline)
-> surrounding/earlier behavior still works
```

## Required Evidence

- exact tests/commands executed, including the full characterization suite;
- actual state/artifacts inspected (not just process exit codes);
- PASS/FAIL per verification area above;
- unresolved issues, explicitly named.

## Gate Failure

If the Gate reveals a defect (including any behavior drift):

1. do not mark the Gate complete;
2. do not patch large unrelated code inside the Gate — only tiny
   verification-only corrections are permitted, and only if this Gate
   explicitly allows them;
3. identify the required remediation as a new/reopened Refactor Step (or,
   if the defect requires an intentional behavior change, escalate it out
   of refactor scope into a FEATURE/BUGFIX work package instead of fixing
   it here);
4. record evidence;
5. STOP.

## Gate PASS

1. mark the Refactor Gate complete in `CURRENT.md`;
2. write the Gate report (per `shared/EXECUTION_RULES.md`), including a
   summary of the architectural improvement achieved and confirmation that
   behavior was preserved;
3. STOP.

Do not start unrelated cleanup or new work in this invocation.
