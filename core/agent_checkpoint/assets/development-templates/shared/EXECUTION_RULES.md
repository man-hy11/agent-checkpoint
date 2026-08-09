# EXECUTION_RULES.md

## One Invocation Rule

One AI coding-agent invocation may execute at most:

```text
one Step
or
one Gate
```

This applies to:

- full projects;
- feature changes;
- bug fixes.

## Successful Completion

After the current execution unit passes all required Tasks/checks, tests, evidence checks, and acceptance criteria:

1. mark the current unit complete;
2. update the authoritative Current Target to the next Step/Gate;
3. write the completion report;
4. STOP immediately.

Advancing Current Target does not authorize work on the next target in the same invocation.

## Forbidden Same-Invocation Work

After completing the current Step/Gate, do not:

- start the next Step;
- implement code only needed by the next Step;
- run tests solely for the next Step;
- begin the next Gate;
- begin the next project Phase;
- begin an unrelated cleanup/refactor.

Reading the next target only to record its name is allowed.

## Failure Rule

If any required check fails:

1. leave the execution unit incomplete;
2. do not advance Current Target;
3. preserve useful failure evidence;
4. document exact failure/remediation;
5. STOP.

## Scope Rule

Implement only the current execution unit.

Future work is allowed only where the current unit explicitly requires a:

- schema;
- interface;
- abstraction;
- migration foundation;
- compatibility contract.

## Validation Rule

Source inspection alone is not completion proof.

Use the appropriate mix of:

- unit tests;
- integration tests;
- build;
- lint/typecheck;
- migration tests;
- API tests;
- browser/UI tests;
- worker/job tests;
- database inspection;
- artifact inspection;
- provider contract tests;
- runtime smoke tests;
- manual verification when automation is impractical.

## Completion Report

Every invocation ends with:

```text
Execution Unit
Tasks/checks completed
Files created/modified
Tests/checks executed
PASS/FAIL results
Evidence inspected
Acceptance criteria
Deviations/unresolved issues
Tracker update
Next Target
```

Then STOP.
