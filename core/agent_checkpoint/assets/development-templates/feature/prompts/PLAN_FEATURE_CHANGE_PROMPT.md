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
6. One invocation = one Feature Step or Feature Gate.
7. PASS -> advance `CURRENT.md` -> completion report -> STOP.
8. FAIL -> do not advance -> report remediation -> STOP.
9. The Feature Gate must verify both the new behavior and important existing behavior.
10. Do not begin feature implementation while creating the plan.

If the feature is genuinely tiny, use fewer Steps rather than artificially creating many.
