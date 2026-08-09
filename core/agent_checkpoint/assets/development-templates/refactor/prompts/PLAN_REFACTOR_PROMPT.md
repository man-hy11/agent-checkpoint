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
6. do not start implementation while creating the plan.
