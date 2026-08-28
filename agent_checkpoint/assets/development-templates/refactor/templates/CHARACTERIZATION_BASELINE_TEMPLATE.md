# CHARACTERIZATION_BASELINE.md

## Purpose

Freeze the important existing behavior before structural change.

## Public / Observable Contracts

- API responses/status:
- CLI behavior:
- UI behavior:
- database semantics:
- emitted events/jobs:
- files/artifacts:
- error categories:
- performance-sensitive behavior:

## Existing Test Coverage

| Behavior | Existing Test | Confidence | Missing Coverage |
|---|---|---:|---|
| ... | ... | ... | ... |

## Characterization Tests to Add

- ...

These tests capture intended/current behavior. If an existing behavior is known to be wrong, do not encode it as a permanent invariant; move that behavior change to BUGFIX/FEATURE scope.

## Refactor Success Condition

After structural changes:

```text
same intended external behavior
+ improved internal structure
+ characterization/regression suite still passes
```
