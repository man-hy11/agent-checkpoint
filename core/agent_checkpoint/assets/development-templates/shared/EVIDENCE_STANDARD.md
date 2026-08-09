# EVIDENCE_STANDARD.md

## Principle

A coding agent must distinguish:

```text
"I changed the code"
```

from:

```text
"I verified the intended behavior"
```

## Minimum Evidence Per Task

Record:

- exact files changed;
- exact command(s) run;
- PASS/FAIL;
- actual output/state inspected;
- relevant API/DB/UI/artifact state;
- deviations from specification;
- unresolved risks.

## Strong Evidence Examples

### Backend

- HTTP response body/status;
- database row/state;
- migration applied and rolled forward in test DB;
- worker job state;
- normalized error category.

### Frontend

- component test result;
- browser state;
- route behavior;
- loading/empty/error state;
- persistence after reload.

### File/media/artifact

- output file exists;
- output metadata validated;
- checksum/size;
- parser/prober result;
- artifact state.

### External integration

Prefer:

- fake provider;
- contract test;
- sandbox/test account;
- idempotency/reconciliation evidence.

Do not use destructive production calls as casual verification.

## Evidence and Failures

Do not hide failures by:

- rerunning until one PASS appears without explaining prior failures;
- weakening assertions;
- disabling tests;
- swallowing exceptions;
- changing acceptance criteria after implementation.

If a test is flaky, record that fact and fix/isolate the flakiness where required.
