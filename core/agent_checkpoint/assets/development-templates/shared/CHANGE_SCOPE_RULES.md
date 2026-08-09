# CHANGE_SCOPE_RULES.md

## Existing Project First

For feature/bug work:

1. inspect the existing repository;
2. identify current architecture and source-of-truth documents;
3. identify affected modules;
4. identify existing tests/contracts;
5. plan the smallest coherent change.

Do not impose a new architecture merely because the template uses different terminology.

## Avoid Unrelated Changes

Do not:

- perform unrelated refactors;
- reformat large unrelated files;
- upgrade unrelated dependencies;
- rename broad APIs without need;
- change public behavior outside the requested scope.

## Preserve Existing Invariants

The change plan must identify and preserve:

- current authentication/authorization;
- data ownership;
- state machines;
- persistence semantics;
- backward compatibility;
- external side-effect rules;
- provider abstractions;
- deployment constraints.

## Change Boundary

Every feature/bug plan should explicitly list:

```text
In Scope
Out of Scope
Expected Files/Modules
Potentially Affected Interfaces
Regression Surface
```
