Use the supplied **AI Development Templates / Feature Change Template** to plan this feature addition/change in the existing repository.

Do not implement the feature yet.

First inspect the existing project:

- root agent instructions;
- current architecture and source-of-truth docs;
- affected modules;
- existing tests;
- data/contracts;
- UI/API behavior;
- relevant recent change conventions.

Then create an independent Feature Change package under an appropriate path such as:

```text
changes/FEATURE-YYYY-NNN-<slug>/
```

Create:

- `CHANGE.md`
- `CURRENT.md`
- `IMPACT.md`
- detailed `step-F1.md`, `step-F2.md`, ...
- `gate.md`
- `FIRST_RUN_PROMPT.md`
- `CONTINUE_PROMPT.md`

Rules:

1. F1 should normally inspect/confirm existing behavior and impact before implementation.
2. Split implementation by coherent risk/dependency boundaries.
3. Include regression surfaces in every implementation Step.
4. Preserve existing architecture unless the requested feature genuinely requires a deliberate architecture change.
5. Avoid unrelated refactors.
6. every Step must follow `templates/FEATURE_STEP_TEMPLATE.md` in full — do not
   emit a thin summary. Each Step needs:
   - Required Reading (this Feature's `CHANGE.md`/`IMPACT.md` plus relevant
     repo docs) and explicit In/Out of Scope;
   - Tasks broken out per `shared/TASK_DECOMPOSITION_STANDARD.md` (Objective,
     Inspect Before Editing with concrete existing paths from `IMPACT.md`,
     Implementation Contract, numbered Detailed Implementation Steps,
     Failure/Recovery Cases with error code/message/retryability/cleanup/
     final-state, Task-Level Test Cases, Evidence Required, Task Done
     Condition);
   - a Task Execution Tracking table;
   - the relevant sections of `shared/CROSS_CUTTING_CONTRACTS.md` (Architecture
     Fit, Expected Files/Modules, Data/Persistence, API Contract,
     Worker/Background Contract, Configuration, Error Handling Matrix,
     Logging/Observability) — filled in, not left as placeholders, for every
     section that applies to this Step's actual behavior;
   - the Implementation Review Checklist from `shared/STEP_EXECUTION_PROTOCOL.md`,
     feature-adapted;
7. every Feature Gate must follow `templates/FEATURE_GATE_TEMPLATE.md` in
   full, per `shared/GATE_STANDARD.md`;
8. `CURRENT.md` is authoritative;
9. one invocation = one Feature Step or Feature Gate;
10. PASS -> advance `CURRENT.md` -> completion report -> STOP.
11. FAIL -> do not advance -> report remediation -> STOP.
12. The Feature Gate must verify both the new behavior and important existing behavior.
13. Do not begin feature implementation while creating the plan.

A Step that is thin because the underlying change is genuinely small (few
Tasks, no persistence/API/worker surface) is correct — omit inapplicable
Cross-Cutting Contracts sections rather than padding them, and use fewer
Steps rather than artificially creating many. A Step that omits detail
because it involves real persistence, API, worker, or failure-prone
behavior is not acceptable.
