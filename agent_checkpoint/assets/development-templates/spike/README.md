# Spike / Research / POC Template

Use this workflow for **answering technical feasibility questions, comparing architectures/libraries, or building bounded proof-of-concepts before committing**.

Recommended work package:

```text
changes/SPIKE-YYYY-NNN-<slug>/
```

Default lifecycle:

```text
S1 Question / Decision Criteria
-> S2 Alternatives / Evidence Plan
-> S3 Bounded Experiments
-> S4 Findings / Tradeoffs
-> S5 Recommendation / Decision Record
-> Spike Gate
```

## Hard Rules

- The output is evidence and a decision, not production code.
- Define the question and decision criteria before experimenting.
- Time/scope-box experiments.
- Compare realistic alternatives where feasible.
- Record failed experiments and uncertainty.
- Prototype code must not silently become production code.
- If a prototype is selected, create a normal PROJECT/FEATURE/REFACTOR/INTEGRATION plan to productionize it.

All execution uses:

```text
one AI invocation = one Step or one Gate
```

PASS advances `CURRENT.md` to the next target and then STOPs.
FAIL does not advance.
