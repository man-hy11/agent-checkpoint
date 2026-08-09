# Bug Gate — <BUG TITLE>

## Preconditions

B1-B4 (or generated Bugfix Steps) are verified complete.

## Verify

### Original User Scenario
Repeat the original scenario.

### Regression Protection
Confirm the new/updated test fails on the broken behavior conceptually and passes with the fix.

### Root Cause Alignment
Confirm the implemented fix matches the evidence-backed cause.

### Neighboring Behavior
Run the agreed regression surface.

### Scope Audit
Confirm no unrelated changes were introduced.

## Required Evidence

- original reproduction result;
- regression test result;
- relevant suite result;
- changed files;
- remaining limitations.

## Gate Result

PASS:
- mark Bug Gate complete;
- write final bugfix summary;
- STOP.

FAIL:
- do not mark complete;
- identify remediation;
- STOP.
