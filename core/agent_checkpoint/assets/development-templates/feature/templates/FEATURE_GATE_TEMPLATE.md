# Feature Gate — <FEATURE NAME>

## Preconditions

All Feature Steps are verified complete.

## Verify

### Requested Feature
- ...

### Existing Behavior / Regression
- ...

### Data / Migration
- ...

### Security / Permissions
- ...

### UI / API Compatibility
- ...

### Failure / Rollback
- ...

## Representative E2E

```text
existing workflow
-> new feature
-> expected result
-> existing surrounding behavior still works
```

## Required Evidence

- commands/tests;
- actual output/state;
- regression evidence;
- changed files;
- unresolved issues.

## Gate Result

PASS:
- mark Feature Gate complete;
- record final summary;
- STOP.

FAIL:
- do not mark complete;
- identify required remediation/new Step;
- STOP.
