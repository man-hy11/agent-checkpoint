Use the supplied **AI Development Templates / Bugfix Template** to plan this bug investigation and fix in the existing repository.

Do not implement the fix yet.

First inspect:

- existing repository agent instructions;
- affected architecture/modules;
- existing tests;
- relevant logs/errors;
- user-provided reproduction details;
- version/config/environment.

Create an independent package such as:

```text
changes/BUG-YYYY-NNN-<slug>/
```

Create:

- `BUG.md`
- `CURRENT.md`
- detailed bugfix Steps;
- `gate.md`
- `FIRST_RUN_PROMPT.md`
- `CONTINUE_PROMPT.md`

Default Step structure:

```text
B1 Reproduce & Capture Evidence
B2 Root Cause Analysis
B3 Minimal Fix
B4 Regression & Related Behavior
Bug Gate
```

Adjust the number of Steps only when complexity requires it.

Hard rules:

1. When reproduction/evidence is reasonably obtainable, do not enter Fix before Root Cause is evidence-backed.
2. Do not treat a plausible hypothesis as confirmed root cause.
3. Do not make broad unrelated refactors.
4. The Fix Step should be minimal and aligned to the confirmed cause.
5. Add/strengthen a regression test where practical.
6. Bug Gate must repeat the original scenario and verify adjacent behavior.
7. One invocation = one Bugfix Step or Bug Gate.
8. PASS -> advance CURRENT.md -> report -> STOP.
9. FAIL -> do not advance -> report remediation -> STOP.
10. Do not implement the fix while creating this plan.

If reproduction is impossible due to missing environment/data, create an explicit evidence-gathering/blocker path instead of guessing.
