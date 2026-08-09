You are implementing the project from the specifications in this repository.

Read:

1. `AGENTS.md`
2. `CLAUDE.md` if applicable
3. `PHASE.md`
4. `docs/DEVELOPMENT_PLAN.md`
5. `docs/TASK_EXECUTION_STANDARD.md`
6. the current Step/Gate prompt and referenced cross-cutting documents

Execute ONLY the Current Target from `PHASE.md`.

For each required Task/check:

```text
inspect
-> implement when this is a Step
-> focused tests/verification
-> inspect actual result/state
-> record evidence
-> verify
```

Rules:

- one invocation = one Step or one Phase Gate;
- do not begin the next target;
- update `PHASE.md` only after verified PASS;
- if anything fails, leave current target incomplete;
- after the completion report, STOP.

Do not begin the next execution unit automatically.
