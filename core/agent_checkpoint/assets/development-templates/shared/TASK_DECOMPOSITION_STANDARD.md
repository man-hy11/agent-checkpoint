# TASK_DECOMPOSITION_STANDARD.md

## Purpose

A Step is the execution unit an agent may complete in one invocation. A Step is not
itself the unit of implementation work — it is composed of Tasks. Each Task is a
single coherent piece of behavior that can be inspected, implemented, tested, and
verified on its own.

Splitting a Step into Tasks is what keeps a large Step reviewable and keeps the
agent from silently expanding scope mid-Step.

## When to Split a Step Into Multiple Tasks

Split when the Step's Implement/Detailed Work section would otherwise mix:

- more than one persistence-affecting behavior;
- more than one externally observable contract (API, schema, UI state);
- setup/schema work and business logic in the same paragraph;
- a happy-path behavior and its dedicated failure/retry handling.

Do not split a genuinely small Step into artificial Tasks merely to satisfy this
standard — a one-Task Step is correct when the work is one coherent unit.

## Per-Task Structure

Every Task in a Step must contain:

```text
### Task N — <imperative, specific action>

#### Objective
One sentence: what this Task alone must accomplish.

#### Inspect Before Editing
- exact files/modules this Task is expected to touch or extend;
- note: if an equivalent module already exists under a different path,
  extend it and record the mapping in the completion report instead of
  creating a parallel implementation.

#### Implementation Contract
- accepted inputs;
- returned outputs / persisted state;
- invariants that must hold before and after;
- error categories this Task owns.

#### Detailed Implementation Steps
Numbered, concrete steps — not restatement of the Objective. Include, where
applicable:
1. inspect current ownership (types, persistence, side effects, callers, tests)
   before adding new modules;
2. confirm the contract above before writing code;
3. implement only this Task's behavior — do not pull forward-Step scope in;
4. keep orchestration separate from low-level adapters so core logic is
   unit-testable without network/DB/browser/paid-provider dependencies where
   practical;
5. validate external/boundary inputs before irreversible side effects;
6. make partial-failure behavior explicit — the system must end in a state
   that can be inspected and safely retried or corrected;
7. add stable structured log context (no secrets);
8. add focused automated tests for success, boundary conditions, and
   meaningful failures;
9. verify through the real owning code path, not only in isolation.

#### Failure / Recovery Cases
List each realistic failure for this Task. For each one, specify:
- error category/code;
- safe user-facing message (if user-facing);
- internal log context;
- retryability;
- cleanup/compensation action;
- final resulting state.

#### Task-Level Test Cases
- the success path;
- each boundary condition relevant to this Task;
- each failure case above;
- assert persisted/resulting state or artifact, not only a return code;
- unit tests must not require live paid external providers unless explicitly
  marked as opt-in integration tests.

#### Evidence Required Before Checking This Task
- exact test/build command(s) executed;
- PASS/FAIL result;
- key artifact/state inspected (DB row, object metadata, API response,
  UI reload state, metrics, etc.);
- any deviation from this Task's contract and why it was necessary.

#### Task Done Condition
Implemented through the normal production code path, its main failure modes
are explicit, and its focused tests pass. Placeholder code, mocks left in a
production path, or unresolved TODOs do not satisfy this condition.
```

## Task Execution Tracking

Every Step with more than one Task must include a tracking table:

```markdown
| Task | Code | Focused Tests | Integration Evidence | Verified |
|---|---|---|---|---|
| 1. <name> | [ ] | [ ] | [ ] | [ ] |
| 2. <name> | [ ] | [ ] | [ ] | [ ] |
```

A Task row is checked only when every column for it is true.
