# Refactor Template

Use this workflow for **improving internal design, maintainability, modularity, ownership boundaries, or code health while preserving intended behavior**.

Recommended work package:

```text
changes/REFACTOR-YYYY-NNN-<slug>/
```

Default lifecycle:

```text
R1 Baseline & Characterization
-> R2 Refactor Design / Boundaries
-> R3 Incremental Refactor
-> R4 Regression / Cleanup
-> Refactor Gate
```

## Hard Rules

- Intended externally observable behavior must remain unchanged unless explicitly declared.
- Establish characterization/regression coverage before risky restructuring.
- Refactor incrementally; keep the code runnable/testable between Steps.
- Do not mix unrelated feature work or bug fixes into the refactor.
- If behavior must intentionally change, split that work into FEATURE or BUGFIX.

All execution uses:

```text
one AI invocation = one Step or one Gate
```

PASS advances `CURRENT.md` to the next target and then STOPs.
FAIL does not advance.
