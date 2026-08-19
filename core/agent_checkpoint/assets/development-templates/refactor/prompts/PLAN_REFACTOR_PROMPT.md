Use the supplied **AI Development Templates / Refactor Template** to plan this work.

Do not execute the change yet.

First inspect the existing repository and gather the context needed to plan safely.

Create an independent work package such as:

```text
changes/REFACTOR-YYYY-NNN-<slug>/
```

Create:

- `WORK.md` or a more specific work-description file;
- `CURRENT.md`;
- detailed Step prompts;
- `gate.md`;
- `FIRST_RUN_PROMPT.md`;
- `CONTINUE_PROMPT.md`.

Default conceptual Steps:

```text
R1 Baseline & Characterization
R2 Refactor Design / Boundaries
R3 Incremental Refactor
R4 Regression / Cleanup
Refactor Gate
```

Adjust Step count to the actual complexity.

Planning focus:

improving internal design, maintainability, modularity, ownership boundaries, or code health while preserving intended behavior

Hard rules:

- Intended externally observable behavior must remain unchanged unless explicitly declared.
- Establish characterization/regression coverage before risky restructuring.
- Refactor incrementally; keep the code runnable/testable between Steps.
- Do not mix unrelated feature work or bug fixes into the refactor.
- If behavior must intentionally change, split that work into FEATURE or BUGFIX.

Execution rules:

1. one invocation = one Refactor Step or one Refactor Gate;
2. PASS -> advance `CURRENT.md` -> completion report -> STOP;
3. FAIL -> do not advance -> remediation report -> STOP;
4. do not perform unrelated refactors or product changes;
5. include evidence and regression requirements in every Step;
6. do not start implementation while creating the plan;
7. every Step must follow `templates/STEP_TEMPLATE.md` in full — do not emit
   a thin summary. Each Step needs:
   - Required Reading / Existing System Inspection, including
     `CHARACTERIZATION_BASELINE.md` for its affected surface, and explicit
     In/Out of Scope;
   - Tasks broken out per `shared/TASK_DECOMPOSITION_STANDARD.md`
     (Objective, Inspect Before Editing with concrete paths, Implementation
     Contract stating what behavior is preserved, numbered Detailed
     Implementation Steps that capture a pre-change baseline run and a
     post-change confirmation run, Failure/Recovery Cases with error
     code/message/retryability/cleanup/final-state, Task-Level Test Cases
     including the relevant characterization tests, Evidence Required, Task
     Done Condition);
   - a Task Execution Tracking table;
   - the relevant sections of `shared/CROSS_CUTTING_CONTRACTS.md` (Data/
     Persistence, API Contract, Worker/Background Contract, Configuration,
     Error Handling Matrix, Logging/Observability) — filled in, not left as
     placeholders, for every section that applies to this Step's
     restructuring, each stating explicitly what is NOT changing;
   - the Regression/Compatibility Surface naming the exact characterization
     tests covering this Step;
   - the Implementation Review Checklist from `templates/STEP_TEMPLATE.md`
     (baseline items plus the refactor-specific items: characterization
     tests existed before the change, full suite passes unchanged after,
     no duplicate/parallel implementation left behind, no unrelated feature
     work folded in, any accidental behavior change reverted or escalated);
8. the Refactor Gate must follow `templates/GATE_TEMPLATE.md` in full, per
   `shared/GATE_STANDARD.md` — Primary Outcome (architectural improvement),
   Existing Behavior/Compatibility, Failure/Recovery, Security/Data/
   Operations, Cross-Step Regression, Backward Compatibility, Observability,
   Representative End-to-End, and Required Evidence, all filled in rather
   than left as placeholders.

A Step that is thin because the underlying restructuring is genuinely small
(few Tasks, no persistence/API/worker surface touched) is correct — omit
inapplicable Cross-Cutting Contracts sections rather than padding them. A
Step that omits detail because it involves real characterization risk,
persistence, API, worker, or failure-prone behavior is not acceptable.
